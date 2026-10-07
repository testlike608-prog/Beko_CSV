"""
realtime.py
-----------
طبقة Socket.IO — بتستبدل كل الـ polling اللي كان في الواجهة.

الفكرة:
    بدل ما كل تاب يسأل السيرفر كل ثانية (9 لوبات مختلفة!)، السيرفر بيقرأ
    الحالة في تاسك واحد في الخلفية، وبيبعت *بس لما تتغيّر*. النتيجة:
    ترافيك أقل بكتير وقت السكون، ووصول أسرع (500ms بدل 1-2 ثانية).

ملاحظات مهمة:

1) الـ import بتاع socketio متغلّف في try/except عن قصد:
   لو المكتبة مش متسطبة، التطبيق بيفضل شغال عادي على الـ REST endpoints
   القديمة (لسه موجودة كلها)، والواجهة بترجع للـ polling أوتوماتيكيًا.

2) /check-flags مكانش مجرد "قراءة"! كان بيعمل:
       cc.Buzzer_Flag_to_OFF = False
   و /control بيخليها True، واللوب في ClientsClass.auto_load_csv_by_product_number
   مستني الفلاج ده عشان يطفي الجرس ويخرج. يعني الـ polling نفسه كان
   جزء من منطق الهاردوير. عشان كده الـ ticker بتاع الفلاجات بيعمل نفس
   الـ reset وبنفس المعدل (ثانية واحدة) — أي تغيير هنا بيأثر على الجرس.

3) /sql_status بيفتح اتصال pyodbc حقيقي بـ timeout=2. ده كان بيتنفذ كل
   ثانيتين لكل تاب مفتوح. دلوقتي بيتنفذ مرة واحدة لكل السيرفر كل 5 ثواني،
   وجوه thread عشان ما يقفلش الـ event loop.
"""

from __future__ import annotations

import asyncio
import traceback
from typing import Any, Optional

try:
    import socketio  # type: ignore
except ImportError:  # المكتبة مش متسطبة — بنكمّل بالـ REST عادي
    socketio = None  # type: ignore


# ----------------------------------------------------------------------
# السيرفر
# ----------------------------------------------------------------------
sio: Optional[Any] = None

if socketio is not None:
    sio = socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins="*",
        # الواجهة كلها على نفس الأوريجين، فمفيش داعي للوج الكتير
        logger=False,
        engineio_logger=False,
    )


def is_enabled() -> bool:
    return sio is not None


# آخر نسخة اتبعتت من كل حدث — عشان ما نبعتش غير التغييرات
_last_payload: dict = {}
_tasks: list = []


async def _emit_if_changed(event: str, payload: dict, force: bool = False):
    """بيبعت الحدث بس لو الداتا اتغيّرت عن آخر مرة."""
    if sio is None:
        return
    if not force and _last_payload.get(event) == payload:
        return
    _last_payload[event] = payload
    await sio.emit(event, payload)


# ----------------------------------------------------------------------
# بناء الحالة (نفس اللي كانت الـ endpoints بترجعه بالظبط)
# ----------------------------------------------------------------------
def build_process_state() -> dict:
    from process_control import controller
    from fastapi_app.core import BOOT_ID

    return {**controller.status(), "boot_id": BOOT_ID}


def build_station_state(station: int) -> dict:
    import ClientsClass as cc
    from process_control import controller

    if station == 1:
        return {
            "arrived": cc.your_s1_arrived_flag,
            "result": cc.your_s1_result,
            "failed_tests": getattr(cc, "your_s1_failed_tests", None),
            "dummy_number": cc.your_s1_dummy,
            "sku_number": cc.your_s1_sku,
            "process_running": controller.is_running(),
        }
    return {
        "arrived": cc.your_s2_arrived_flag,
        "result": cc.your_s2_result,
        "failed_tests": getattr(cc, "your_s2_failed_tests", None),
        "dummy_number": cc.your_s2_dummy,
        "sku_number": cc.your_s2_sku,
        "process_running": controller.is_running(),
    }


def build_flags_state() -> tuple[dict, dict]:
    """
    نفس منطق /check-flags و /check-flags2 — *بما فيه* الـ side effect.
    شوف الملاحظة رقم (2) فوق: الـ reset ده جزء من منطق إطفاء الجرس.
    """
    import ClientsClass as cc

    cc.Buzzer_Flag_to_OFF = False

    flags1 = {
        "manual_scanner": cc.Manual_Scanner_MODE,
        "no_csv_error": cc.NO_CSV_ERROR,
        "no_csv_file": getattr(cc, "NO_CSV_FILE", None),
        "scan_skipped": getattr(cc, "SCAN_SKIPPED", False),
        "scan_skipped_count": getattr(cc, "SCAN_SKIPPED_COUNT", 0),
    }
    flags2 = {
        "manual_scanner": cc.Manual_Scanner_MODE2,
        "no_csv_error": cc.NO_CSV_ERROR2,
        "no_csv_file": getattr(cc, "NO_CSV_FILE2", None),
        "scan_skipped": getattr(cc, "SCAN_SKIPPED2", False),
        "scan_skipped_count": getattr(cc, "SCAN_SKIPPED_COUNT2", 0),
    }
    return flags1, flags2


def _build_sql_state_blocking() -> dict:
    """بيفتح اتصالات فعلية — لازم يتنادى جوه thread مش على الـ event loop."""
    import db
    import pyodbc

    db1_connected = False
    db2_connected = False

    if db.conn_str_db1_global:
        try:
            with pyodbc.connect(db.conn_str_db1_global, timeout=2):
                pass
            db1_connected = True
        except Exception:
            db1_connected = False

    if db.conn_str_db2_global:
        try:
            with pyodbc.connect(db.conn_str_db2_global, timeout=2):
                pass
            db2_connected = True
        except Exception:
            db2_connected = False

    return {"db1_connected": db1_connected, "db2_connected": db2_connected}


# ----------------------------------------------------------------------
# اللوبات
# ----------------------------------------------------------------------
async def _fast_loop(interval: float = 0.5):
    """حالة العملية + المحطتين — أسرع من الـ polling القديم (كان 1-2 ثانية)."""
    while True:
        try:
            await _emit_if_changed("process_status", build_process_state())
            await _emit_if_changed("station1", build_station_state(1))
            await _emit_if_changed("station2", build_station_state(2))
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(interval)


async def _flags_loop(interval: float = 1.0):
    """
    الفلاجات — بنفس معدل الـ polling القديم (ثانية) *عن قصد*،
    لأن الـ reset بتاع Buzzer_Flag_to_OFF مربوط بالتوقيت ده.
    """
    while True:
        try:
            flags1, flags2 = build_flags_state()
            await _emit_if_changed("flags1", flags1)
            await _emit_if_changed("flags2", flags2)
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(interval)


async def _sql_loop(interval: float = 5.0):
    """اتصال قاعدة البيانات — تقيل، فبمعدل أبطأ وجوه thread."""
    while True:
        try:
            state = await asyncio.to_thread(_build_sql_state_blocking)
            await _emit_if_changed("sql_status", state)
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(interval)


# ----------------------------------------------------------------------
# دورة الحياة
# ----------------------------------------------------------------------
def register_handlers():
    if sio is None:
        return

    @sio.event
    async def connect(sid, environ, auth=None):  # noqa: ARG001
        """أول ما تاب يتصل، نبعتله صورة كاملة من الحالة فورًا."""
        try:
            await sio.emit("process_status", build_process_state(), to=sid)
            await sio.emit("station1", build_station_state(1), to=sid)
            await sio.emit("station2", build_station_state(2), to=sid)

            flags1, flags2 = build_flags_state()
            await sio.emit("flags1", flags1, to=sid)
            await sio.emit("flags2", flags2, to=sid)

            cached_sql = _last_payload.get("sql_status")
            if cached_sql is not None:
                await sio.emit("sql_status", cached_sql, to=sid)
        except Exception:
            traceback.print_exc()


def start_tickers():
    if sio is None:
        print("[realtime] python-socketio غير متسطب — الواجهة هترجع للـ polling")
        return

    loop = asyncio.get_event_loop()
    _tasks.append(loop.create_task(_fast_loop()))
    _tasks.append(loop.create_task(_flags_loop()))
    _tasks.append(loop.create_task(_sql_loop()))


async def stop_tickers():
    for task in _tasks:
        task.cancel()
    for task in _tasks:
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    _tasks.clear()
