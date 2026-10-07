"""
process_control.py
------------------
وحدة التحكم في تشغيل/إيقاف عملية خط الإنتاج (Start / Stop).

الفكرة:
    - عند الضغط على Start: نعمل instance جديد من ClientsClass.App،
      نفتح كل الاتصالات، ونشغّل tasks القراءة/المعالجة على loop العملية.
    - عند الضغط على Stop: نرفع علم الإيقاف، نلغي كل الـ tasks، نطفي
      كل المخارج، ونقفل السوكيتات.

كل شغل العملية بيحصل على event loop واحد (async_runtime) بدل ثريد لكل
حاجة. الدوال العامة هنا (start / stop / request_stop / status ...) لسه
عادية (sync) عشان الراوترات وسيرفر الويب ينادوها زي ما هم من غير تعديل.

الوحدة دي مستقلة تمامًا عن FastAPI/Flask عشان تقدر تستخدمها من أي مكان.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Optional

import async_runtime
import ClientsClass as cc
import vision_master
from vision_master import VisionMasterError


class ProcessController:
    """يدير دورة حياة عملية خط الإنتاج. آمن للنداء من أي ثريد في سيرفر الويب."""

    # أقصى وقت نسيب فيه الواجهة مقفولة أثناء الإيقاف
    STOP_WATCHDOG = 15.0

    def __init__(self):
        # threading.RLock مش asyncio.Lock: الحالة بتتقري من ثريدات سيرفر الويب
        # كمان، ومفيش أي await جوه أي حتة ماسكة الـ lock.
        self._lock = threading.RLock()
        self._app: Optional[cc.App] = None
        self._boot_future = None          # concurrent.futures.Future للـ _boot
        self._running = False
        self._ready = False           # خلص Start_connetion وفتح الاتصالات
        self._stopping = False        # الإيقاف شغال في الخلفية دلوقتي
        self._started_at: Optional[float] = None
        self._last_error: Optional[str] = None

    # ------------------------------------------------------------------
    # الحالة
    # ------------------------------------------------------------------
    @property
    def app(self) -> Optional[cc.App]:
        return self._app

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def status(self) -> dict:
        """حالة مفصّلة تُعرض في الواجهة."""
        with self._lock:
            clients = {}
            workers = 0
            if self._app is not None:
                for name, client in (
                    ("scanner_s1", self._app.client_scanner_station1),
                    ("scanner_s2", self._app.client_scanner_station2),
                    ("vision_s1", self._app.client_Vision_station1),
                    ("vision_s2", self._app.client_Vision_station2),
                    ("io_read", self._app.client_read_io),
                    ("io_write", self._app.client_write_io),
                ):
                    clients[name] = {
                        "connected": bool(client.connected),
                        "endpoint": f"{client.ip}:{client.port}",
                    }
                if self._ready:
                    workers = len(self._app.active_task_names())

            return {
                "running": self._running,
                "ready": self._ready,
                "stopping": self._stopping,
                "state": (
                    "stopping" if self._stopping
                    else "running" if (self._running and self._ready)
                    else "starting" if self._running
                    else "stopped"
                ),
                "started_at": self._started_at,
                "uptime_seconds": (
                    round(time.time() - self._started_at, 1)
                    if (self._running and self._started_at)
                    else 0
                ),
                # الاسم فضل زي ما هو عشان الواجهة — بقى عدد الـ tasks الشغالة
                "worker_threads": workers,
                "clients": clients,
                "vision_master": vision_master.controller.status(),
                "last_error": self._last_error,
            }

    # ------------------------------------------------------------------
    # التشغيل
    # ------------------------------------------------------------------
    def start(self) -> dict:
        """
        بيرجع فورًا. الاتصال بالأجهزة بيحصل كـ task على loop العملية عشان
        Start_connetion ممكن تفضل مستنية جهاز مش متصل لوقت طويل،
        وده كان هيعلّق الـ HTTP request.

        الاستثناء الوحيد هو VisionMaster: بنحمّله *متزامن* هنا قبل أي حاجة
        تانية، عشان لو المسارات غلط أو الترخيص ناقص نوقف من غير ما نفتح أي
        سوكيت، والخطأ يرجع في رد الـ HTTP نفسه بدل ما يضيع في اللوج.
        """
        with self._lock:
            if self._running:
                return {"ok": False, "running": True, "message": "Process is already running"}

            self._last_error = None
            self._ready = False
            self._app = None
            # بنحجز الحالة بدري عشان ما حدش يضغط START مرتين
            # أثناء تحميل الـ .NET assemblies
            self._running = True
            self._started_at = time.time()

        # ------------------------------------------------------------------
        # 1. VisionMaster — بره الـ lock لأن التحميل ممكن ياخد ثواني
        #    والـ lock ده بتستخدمه /process/status كل ثانية.
        # ------------------------------------------------------------------
        try:
            vision_master.controller.prepare()
        except VisionMasterError as exc:
            msg = f"VisionMaster failed: {exc}"
            with self._lock:
                self._running = False
                self._started_at = None
                self._last_error = msg
            return {
                "ok": False,
                "running": False,
                "message": msg,
                "vision_master": vision_master.controller.status(),
            }

        # ------------------------------------------------------------------
        # 2. إنشاء الـ App وتشغيل الإقلاع على loop العملية
        # ------------------------------------------------------------------
        failure: Optional[dict] = None

        with self._lock:
            if not self._running:
                # المستخدم ضغط Stop أثناء تحميل VisionMaster
                failure = {"ok": False, "running": False, "message": "Start cancelled"}
            else:
                try:
                    app = cc.App()
                except Exception as exc:  # noqa: BLE001
                    self._running = False
                    self._started_at = None
                    self._last_error = str(exc)
                    failure = {
                        "ok": False,
                        "running": False,
                        "message": f"Failed to start: {exc}",
                    }
                else:
                    self._app = app
                    self._boot_future = async_runtime.submit(self._boot(app))

        # بره الـ lock عشان ما نعطلش /process/status
        if failure is not None:
            self._safe_vision_stop()
            return failure

        return {"ok": True, "running": True, "message": "Process started"}

    def _safe_vision_stop(self):
        """
        إيقاف VisionMaster من غير ما أي استثناء يوقف مسار الإيقاف.

        الخطأ مبيتطبعش في الترمينال — بيتسجّل في last_error عشان يوصل
        للواجهة. وبنكتبه بس لو مفيش خطأ متسجّل قبله، عشان ما يغطّيش
        السبب الأصلي للفشل (VisionMaster فشل، الـ App مااتعملش … إلخ).
        """
        try:
            vision_master.controller.stop()
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                if not self._last_error:
                    self._last_error = f"Error stopping VisionMaster: {exc}"

    async def _boot(self, app: "cc.App"):
        """يفتح الاتصالات ويشغّل tasks العمل. بيشتغل على loop العملية."""
        try:
            # VisionMaster الأول: هو مش معتمد على اتصالات الـ TCP خالص.
            # Start_connetion بتنتهي بـ send_request(CMD_OFF_ALL) اللي بتنادي
            # ensure_connected() وبتفضل تحاول للأبد لو الـ I/O module مش موصّل —
            # فلو شغّلنا الفلوهات بعديها، الفلوهات مكانتش هتشتغل أبدًا على
            # بنش من غير هاردوير. لو فشلت، الـ except تحت بيوقف كل حاجة.
            # (.NET call بلوكنج -> thread عشان ما يوقفش الـ loop)
            await asyncio.to_thread(vision_master.controller.run)

            await app.Start_connetion()

            if app.is_stopping():
                return

            workers = [
                ("io_read", app._IO_read),
                #("vision_station_2", app._vision_station_2),
                #("vision_station_1", app._vision_station_1),
            ]

            with self._lock:
                # لو المستخدم ضغط Stop أثناء الإقلاع، ما نشغّلش حاجة
                if self._app is not app:
                    return
                for name, target in workers:
                    app.spawn(target(), name=f"beko-{name}")
                self._ready = True

        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._last_error = str(exc)
                if self._app is app:
                    self._running = False
                    self._ready = False
            await asyncio.to_thread(self._safe_vision_stop)
            try:
                await app.shutdown()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # الإيقاف
    # ------------------------------------------------------------------
    async def _stop_async(self, join_timeout: float = 5.0) -> dict:
        with self._lock:
            app = self._app
            boot_future = self._boot_future
            # نصفّر المرجع بدري عشان أي _boot شغال يعرف إنه اتلغى.
            # ونرفع علم الإيقاف حتى لو الـ App لسه ما اتعملش، عشان لو إحنا
            # في نص تحميل VisionMaster فـ start() تعرف إنها اتلغت.
            self._app = None
            self._running = False
            self._ready = False

        # VisionMaster بيتقفل في كل الحالات، حتى لو العملية ما وصلتش لمرحلة App
        await asyncio.to_thread(self._safe_vision_stop)

        if app is None:
            with self._lock:
                self._boot_future = None
                self._started_at = None
            return {"ok": False, "running": False, "message": "Process is not running"}

        # لو الإقلاع لسه واقف جوه ensure_connected() نلغيه
        if boot_future is not None and not boot_future.done():
            boot_future.cancel()

        still_alive: list = []
        try:
            still_alive = await app.shutdown(timeout=join_timeout)
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._last_error = str(exc)

        with self._lock:
            self._boot_future = None
            self._started_at = None

        if still_alive:
            return {
                "ok": True,
                "running": False,
                "message": "Process stopped (some worker tasks are still winding down)",
                "pending_threads": still_alive,
            }

        return {"ok": True, "running": False, "message": "Process stopped"}

    def stop(self, join_timeout: float = 5.0) -> dict:
        """نسخة sync — بتستنى لحد ما الإيقاف يخلص (بيستخدمها الـ shutdown بتاع السيرفر)."""
        return async_runtime.run(self._stop_async(join_timeout), timeout=join_timeout + 10)

    # ------------------------------------------------------------------
    def restart(self) -> dict:
        if self.is_running():
            self.stop()
            time.sleep(0.5)
        return self.start()

    # ------------------------------------------------------------------
    # نسخ غير محجوبة للواجهة
    #
    # stop() ممكن تاخد لحد 5 ثواني (إلغاء الـ tasks) وأحيانًا أكتر لو
    # VisionMaster اتأخر. الواجهة كانت بتفضل مستنية الرد وكل الأزرار
    # مقفولة — وده اللي بيبان كأنه تعليق.
    #
    # دلوقتي بنرجع فورًا والإيقاف بيكمّل كـ task على loop العملية، والحالة
    # بتوصل للواجهة عن طريق الـ Socket.IO push (أو الـ polling في وضع الـ fallback).
    # ------------------------------------------------------------------
    def request_stop(self) -> dict:
        with self._lock:
            if self._stopping:
                return {
                    "ok": True,
                    "running": self._running,
                    "message": "Stop already in progress…",
                }
            if not self._running and self._app is None:
                return {"ok": False, "running": False, "message": "Process is not running"}
            self._stopping = True

        async def _worker():
            try:
                await self._stop_async()
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._last_error = str(exc)
            finally:
                with self._lock:
                    self._stopping = False

        async_runtime.submit(self._watch_stopping(_worker()))

        return {"ok": True, "running": False, "message": "Stopping…"}

    async def _watch_stopping(self, worker_coro):
        """
        شبكة أمان: _stopping بيقفل كل أزرار الواجهة. لو الإيقاف علّق
        (مثلاً ContinuousRunEnable=False مرجعش من VisionMaster)، الواجهة
        كانت هتفضل مقفولة للأبد. الووتشدوج بيفك القفل غصبًا.

        بتستخدمها stop و restart الاتنين — restart بينادي stop جواها،
        فعندها نفس احتمال التعليق بالظبط.
        """
        worker = asyncio.ensure_future(worker_coro)
        try:
            # shield: الووتشدوج بيفك القفل بس، مش بيلغي الإيقاف نفسه
            await asyncio.wait_for(asyncio.shield(worker), timeout=self.STOP_WATCHDOG)
        except asyncio.TimeoutError:
            with self._lock:
                if self._stopping:
                    self._stopping = False
                    self._last_error = (
                        "Stop is taking longer than expected — "
                        "still finishing in the background"
                    )
            await worker

    def request_restart(self) -> dict:
        """
        نفس الفكرة: بنرجع فورًا. أي خطأ من start() بيتسجّل في last_error
        واللي بيتبعت للواجهة مع الحالة.
        """
        with self._lock:
            if self._stopping:
                return {"ok": False, "running": self._running, "message": "Stop in progress…"}
            self._stopping = True

        async def _worker():
            # --- مرحلة الإيقاف ---
            try:
                if self.is_running():
                    await self._stop_async()
                    await asyncio.sleep(0.5)
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._last_error = str(exc)
            finally:
                # لازم يتصفّى هنا مهما حصل، وإلا الواجهة تفضل مقفولة
                with self._lock:
                    self._stopping = False

            # --- مرحلة التشغيل ---
            # لو start() فشلت (مثلاً VisionMaster) الرسالة بتبقى في
            # last_error واللي بيوصل للواجهة مع الحالة.
            # start() فيها تحميل VisionMaster (.NET بلوكنج) -> thread
            try:
                await asyncio.to_thread(self.start)
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._running = False
                    self._ready = False
                    self._last_error = str(exc)

        async_runtime.submit(self._watch_stopping(_worker()))

        return {"ok": True, "running": True, "message": "Restarting…"}


# نسخة واحدة مشتركة على مستوى التطبيق كله
controller = ProcessController()
