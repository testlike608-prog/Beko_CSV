"""
vision_master.py
----------------
تشغيل مستمر (Continuous Run) لكل الـ Procedures/Flows في سولوشن VisionMaster —
نسخة بدون واجهة رسومية، مبنية عشان تتنادى من زرار START في الواجهة.

الوحدة دي مستقلة تمامًا عن FastAPI/Qt (زي process_control.py بالظبط)،
وبتتحكم فيها ProcessController.

المتطلبات: pythonnet + VisionMaster متسطب ومرخص + Python 64-bit.

ملاحظة على الامتدادات:
    VisionMaster 4.4  ->  .solw
    VisionMaster 4.3  ->  .sol

مهم:
    - `import clr` بيحصل *جوه* load_vm() مش على مستوى الملف، عشان التطبيق
      يفضل شغال عادي على أي جهاز مش متسطب عليه pythonnet أو VisionMaster.
    - VmSolution كلاس ساكن (static singleton) والـ .NET assemblies مش
      بتتشال من الـ process، فبنحمّل مرة واحدة بس ونعيد الاستخدام.
"""

from __future__ import annotations

import glob
import os
import string
import sys
import threading
import time
import traceback
from typing import Optional

import station_logs


def _flow_station(flow_name: Optional[str]) -> int:
    """الفلو اللي اسمه فيه outer تبع Station 1، واللي فيه inner تبع Station 2."""
    name = (flow_name or "").lower()
    if "outer" in name:
        return 1
    if "inner" in name:
        return 2
    return 0

# ----------------------------------------------------------------------
# اكتشاف المسارات
# ----------------------------------------------------------------------
ASSEMBLY_PATTERNS = [
    r"C:\Program Files\VisionMaster*\Development\V4.x\ComControls\Assembly",
    r"C:\Program Files (x86)\VisionMaster*\Development\V4.x\ComControls\Assembly",
]

SOLUTION_EXTENSIONS = (".solw", ".sol")


def find_assembly_dir() -> str:
    """يدوّر أوتوماتيكيًا على مجلد الاسمبلي (يشتغل مع 4.3 و 4.4 وأي إصدار تاني)."""
    found: list[str] = []
    for pattern in ASSEMBLY_PATTERNS:
        found.extend(glob.glob(pattern))
    found.sort(reverse=True)  # الأحدث أولاً
    for d in found:
        if os.path.isfile(os.path.join(d, "VM.Core.dll")):
            return d
    return ""


def default_solution_guess() -> str:
    """يدوّر على أي ملف سولوشن على الـ Desktop (بما فيه Desktop المحوّل لـ OneDrive)."""
    home = os.environ.get("USERPROFILE", "")
    if not home:
        return ""
    candidates: list[str] = []
    for desktop in (
        os.path.join(home, "Desktop"),
        os.path.join(home, "OneDrive", "Desktop"),
    ):
        if os.path.isdir(desktop):
            for ext in SOLUTION_EXTENSIONS:
                candidates.extend(glob.glob(os.path.join(desktop, f"*{ext}")))
    return candidates[0] if candidates else ""


# ----------------------------------------------------------------------
# تصفّح ملفات الجهاز (للـ Browse في وضع الـ Developer)
#
# ليه من السيرفر مش من المتصفح؟
#   <input type="file"> بيدّي محتوى الملف واسمه بس — المتصفح بيخفي المسار
#   الكامل عن قصد (بيرجّع C:\fakepath\...). و VisionMaster محتاج مسار حقيقي
#   على الديسك. التطبيق شغال على نفس جهاز الخط، فالتصفّح من السيرفر هو الحل
#   الصح واللي بيدي مسار مطلق مضمون.
# ----------------------------------------------------------------------
def list_drives() -> list:
    """قائمة البارتيشنات المتاحة (Windows) أو الجذر (أنظمة تانية)."""
    if os.name != "nt":
        return ["/"]
    drives = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            drives.append(root)
    return drives


def _default_browse_start() -> str:
    """أنسب مكان نبدأ منه التصفّح: الـ Desktop لو موجود، وإلا مجلد المستخدم."""
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    for guess in (
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "Desktop"),
        home,
    ):
        if guess and os.path.isdir(guess):
            return guess
    return ""


def browse_directory(path: str = "", only_dirs: bool = False) -> dict:
    """
    محتويات مجلد على الجهاز اللي شغال عليه التطبيق.

    only_dirs=True  -> للـ Assembly Directory (مجلدات بس، مع تحديد اللي فيه VM.Core.dll)
    only_dirs=False -> للسولوشن (مجلدات + ملفات .sol / .solw بس)
    """
    result = {
        "path": "",
        "parent": None,
        "drives": list_drives(),
        "dirs": [],
        "files": [],
        "only_dirs": bool(only_dirs),
        "error": None,
    }

    path = (path or "").strip()
    if not path:
        path = _default_browse_start()

    if not path:
        # مفيش نقطة بداية — نعرض البارتيشنات بس
        return result

    path = os.path.abspath(path)
    if not os.path.isdir(path):
        result["error"] = f"المجلد غير موجود: {path}"
        return result

    result["path"] = path
    parent = os.path.dirname(path)
    result["parent"] = parent if parent and parent != path else None

    try:
        entries = sorted(os.scandir(path), key=lambda e: e.name.lower())
    except PermissionError:
        result["error"] = f"مفيش صلاحية لفتح: {path}"
        return result
    except OSError as exc:  # noqa: BLE001
        result["error"] = f"تعذّر فتح المجلد: {exc}"
        return result

    for entry in entries:
        try:
            if entry.is_dir():
                item = {"name": entry.name, "path": entry.path}
                if only_dirs:
                    # علامة تساعد المستخدم يلاقي مجلد الاسمبلي الصح
                    try:
                        item["has_vm_core"] = os.path.isfile(
                            os.path.join(entry.path, "VM.Core.dll")
                        )
                    except OSError:
                        item["has_vm_core"] = False
                result["dirs"].append(item)
            elif not only_dirs and entry.name.lower().endswith(SOLUTION_EXTENSIONS):
                result["files"].append(
                    {
                        "name": entry.name,
                        "path": entry.path,
                        "size": entry.stat().st_size,
                    }
                )
        except OSError:
            continue

    return result


def describe_exception(exc: BaseException) -> str:
    """
    وصف تفصيلي للاستثناء بما فيه الـ InnerException بتاع .NET.
    بيرجع نص عشان نقدر نعرضه في الواجهة، مش بيطبع بس.
    """
    lines = [f"{type(exc).__name__}: {exc}"]
    inner = getattr(exc, "InnerException", None)
    depth = 0
    while inner is not None and depth < 5:
        lines.append(f"  INNER[{depth}]: {inner}")
        inner = getattr(inner, "InnerException", None)
        depth += 1
    return "\n".join(lines)


class VisionMasterError(RuntimeError):
    """أي فشل في تحميل أو تشغيل سولوشن VisionMaster."""


# ----------------------------------------------------------------------
# تحميل الاسمبليز (مرة واحدة لكل عملية)
# ----------------------------------------------------------------------
_VmSolution = None
_load_lock = threading.Lock()


def _ensure_python_runtime_next_to_host() -> None:
    """
    بيحط نسخة من Python.Runtime.dll جنب البرنامج المضيف.

    ليه؟ .NET Framework بيدوّر على الاسمبليز في مجلد الأساس بتاع الـ
    AppDomain، وهو مجلد البرنامج اللي شغال. لما بنشتغل من السورس
    المضيف هو python.exe وكل حاجة بتتلاقى عادي. لكن في البناء
    المجمّع، الـ DLL بيبقى في pythonnet\\runtime\\ جوه الحزمة،
    والـ AppDomain مبيلاقيهوش. clr_loader ساعتها بترجع NULL
    والخطأ اللي بيظهر مضلّل:

        Failed to resolve Python.Runtime.Loader.Initialize from <path>

    الرسالة بتطبع المسار اللي حاول يحمّل منه، فبتوحي إن الملف ناقص
    وهو موجود فعلاً — المشكلة في مكانه مش في وجوده.

    ليه وقت التشغيل مش وقت البناء؟ في وضع onefile البرنامج بيتفك في
    فولدر مؤقت وبيشتغل من هناك، فمجلد الأساس بيبقى الفولدر ده — مش
    المكان اللي المستخدم حاطط فيه الـ exe. يعني مفيش مكان ثابت نقدر
    نحط فيه الملف وقت البناء.

    الدالة دي بتشتغل بس في البناء المجمّع. وقت التشغيل من السورس
    مبنعملش حاجة عشان ما نلوّثش مجلد تسطيب بايثون بتاع المستخدم.
    """
    if "__compiled__" not in globals():
        return

    try:
        import pythonnet
    except ImportError:
        return

    package_dir = os.path.dirname(os.path.abspath(pythonnet.__file__))
    source = os.path.join(package_dir, "runtime", "Python.Runtime.dll")
    if not os.path.isfile(source):
        return

    # مكانين محتملين لمجلد الأساس، وبننسخ للاتنين:
    #
    #   1) جذر الحزمة (اللي فيه مجلد pythonnet) — ده مكان البرنامج
    #      اللي بيشتغل فعلاً، وفي onefile ده الفولدر المؤقت.
    #   2) مجلد sys.executable — نفس المكان في standalone، لكن في
    #      onefile ممكن يشاور على الـ exe الأصلي بدل الفولدر المؤقت.
    #
    # التوثيق مش قاطع في سلوك sys.executable مع onefile، والنسخة
    # الزيادة رخيصة، فبنغطي الاحتمالين بدل ما نراهن على واحد.
    candidates = {
        os.path.dirname(package_dir),
        os.path.dirname(os.path.abspath(sys.executable)),
    }

    import shutil

    for host_dir in candidates:
        target = os.path.join(host_dir, "Python.Runtime.dll")
        try:
            if os.path.isfile(target) and os.path.getsize(target) == os.path.getsize(source):
                continue
            shutil.copy2(source, target)
            print(f"[vision_master] Python.Runtime.dll placed in {host_dir}")
        except OSError as exc:
            # مش قاتل — يمكن المجلد التاني ينفع، أو .NET يلاقيه بطريقة تانية.
            # بنطبع عشان لو التحميل فشل بعد كده نعرف السبب.
            print(f"[vision_master] could not place Python.Runtime.dll in {host_dir}: {exc}")


def load_vm(assembly_dir: str):
    """تحميل اسمبليز VisionMaster وإرجاع كلاس VmSolution."""
    global _VmSolution

    with _load_lock:
        if _VmSolution is not None:
            return _VmSolution

        if not assembly_dir:
            raise VisionMasterError(
                "مجلد الاسمبلي مش متظبط. افتح I/O Mapping (Developer) وحدّد المسار."
            )
        if not os.path.isdir(assembly_dir):
            raise VisionMasterError(f"مجلد الاسمبلي غير موجود: {assembly_dir}")

        core = os.path.join(assembly_dir, "VM.Core.dll")
        if not os.path.isfile(core):
            raise VisionMasterError(f"VM.Core.dll غير موجود في: {assembly_dir}")

        _ensure_python_runtime_next_to_host()

        try:
            import clr  # noqa: F401  (pythonnet — بيتحمّل هنا بس)
        except ImportError as exc:
            raise VisionMasterError(
                "pythonnet مش متسطب. شغّل: pip install pythonnet "
                "(لازم Python 64-bit)"
            ) from exc
        except RuntimeError as exc:
            # clr_loader بيرمي RuntimeError لما الـ AppDomain يفشل يحمّل
            # Python.Runtime.dll، والرسالة الأصلية مضلّلة لأنها بتطبع
            # المسار اللي *حاول* يحمّل منه فتوحي إن الملف ناقص.
            raise VisionMasterError(
                "فشل تحميل pythonnet.\n"
                f"{exc}\n\n"
                "لو الرسالة فيها 'Failed to resolve Python.Runtime.Loader.Initialize' "
                "جرّب الآتي:\n"
                "  1) اتأكد إن .NET Framework 4.7.2 أو أحدث متسطب\n"
                "  2) لو نزّلت البرنامج من الإنترنت، شيل علامة الحجب:\n"
                "     Get-ChildItem <مجلد البرنامج> -Recurse | Unblock-File"
            ) from exc

        # الـ DLLs الأصلية (native) بتتحل من PATH مش من sys.path
        if assembly_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = assembly_dir + os.pathsep + os.environ.get("PATH", "")
        if assembly_dir not in sys.path:
            sys.path.append(assembly_dir)

        try:
            clr.AddReference("VM.Core")           # type: ignore[attr-defined]
            clr.AddReference("VM.PlatformSDKCS")  # type: ignore[attr-defined]
            from VM.Core import VmSolution        # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise VisionMasterError(
                f"فشل تحميل اسمبليز VisionMaster من {assembly_dir}\n"
                f"{describe_exception(exc)}"
            ) from exc

        _VmSolution = VmSolution
        return _VmSolution


# ----------------------------------------------------------------------
# قراءة الإعدادات (من config.json عن طريق ioSetting)
# ----------------------------------------------------------------------
def _read_config() -> dict:
    """
    بنستورد ioSetting جوه الدالة عشان نتجنب أي circular import
    ونخلي الموديول ده قابل للاستخدام لوحده.
    """
    try:
        import ioSetting

        return ioSetting.get_vision_master_config()
    except Exception:  # noqa: BLE001
        return {}



# ----------------------------------------------------------------------
# المتحكم
# ----------------------------------------------------------------------
class VisionMasterController:
    """
    يدير دورة حياة سولوشن VisionMaster بشكل thread-safe.

    الاستخدام من ProcessController:
        vision.prepare()   # تحقق + تحميل (متزامن — بيرمي VisionMasterError لو فشل)
        vision.run()       # ContinuousRunEnable = True
        vision.stop()      # ContinuousRunEnable = False + فك الـ handlers
        vision.dispose()   # Dispose نهائي (عند إغلاق التطبيق)
    """

    MAX_LOG = 2000

    def __init__(self):
        self._lock = threading.RLock()
        self._sol_cls = None
        self._flows: list[tuple[str, object]] = []
        # مهم جدًا: نحتفظ بمرجع للـ callbacks وإلا الـ GC بيمسحها
        self._handlers: list[tuple[object, object]] = []
        self._counters: dict[str, int] = {}
        self._loaded = False
        self._running = False
        self._last_error: Optional[str] = None
        self._assembly_dir = ""
        self._solution_path = ""
        self._log: list[tuple[float, str, str]] = []
        self._log_lock = threading.Lock()

    # ------------------------------------------------------------------
    # اللوج
    # ------------------------------------------------------------------
    # مستويات بتتحفظ في اللوج بس ومش بتتطبع في التيرمنال — الـ RUN بيتكرر
    # مع كل دورة للفلو وكان مزحّم التيرمنال
    QUIET_LEVELS = {"RUN"}

    def _log_add(self, level: str, msg: str, flow_name: Optional[str] = None):
        with self._log_lock:
            self._log.append((time.time(), level, msg))
            if len(self._log) > self.MAX_LOG:
                self._log = self._log[-(self.MAX_LOG // 2):]
        if level not in self.QUIET_LEVELS:
            print(f"[VisionMaster][{level}] {msg}")
            # تحذيرات وأخطاء فلو معيّن بتظهر كمان تحت كارت محطته
            station = _flow_station(flow_name)
            if station and level in ("WARNING", "ERROR"):
                station_logs.add(station, f"VM:{flow_name}", level, msg)

    def logs(self, limit: int = 200) -> list[dict]:
        with self._log_lock:
            tail = self._log[-limit:]
        return [{"ts": ts, "level": lvl, "msg": msg} for ts, lvl, msg in tail]

    # ------------------------------------------------------------------
    # الحالة
    # ------------------------------------------------------------------
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def status(self) -> dict:
        with self._lock:
            flows = [
                {"name": name, "runs": self._counters.get(name, 0)}
                for name, _ in self._flows
            ]
            return {
                "loaded": self._loaded,
                "running": self._running,
                "assembly_dir": self._assembly_dir,
                "solution_path": self._solution_path,
                "flow_count": len(flows),
                "flows": flows,
                "last_error": self._last_error,
            }

    # ------------------------------------------------------------------
    # التحقق من المسارات
    # ------------------------------------------------------------------
    @staticmethod
    def check_paths(assembly_dir: str, solution_path: str) -> dict:
        """
        فحص المسارات من غير ما نحمّل أي حاجة — بتستخدمها الواجهة (Developer mode)
        عشان تدي فيدباك فوري قبل الضغط على START.
        """
        report = {
            "assembly_dir": assembly_dir,
            "assembly_dir_exists": bool(assembly_dir) and os.path.isdir(assembly_dir),
            "vm_core_found": False,
            "solution_path": solution_path,
            "solution_exists": bool(solution_path) and os.path.isfile(solution_path),
            "solution_size": 0,
            "errors": [],
        }

        if not assembly_dir:
            report["errors"].append("مجلد الاسمبلي فاضي")
        elif not report["assembly_dir_exists"]:
            report["errors"].append(f"مجلد الاسمبلي غير موجود: {assembly_dir}")
        else:
            report["vm_core_found"] = os.path.isfile(
                os.path.join(assembly_dir, "VM.Core.dll")
            )
            if not report["vm_core_found"]:
                report["errors"].append(f"VM.Core.dll غير موجود في: {assembly_dir}")

        if not solution_path:
            report["errors"].append("مسار السولوشن فاضي")
        elif not report["solution_exists"]:
            report["errors"].append(f"ملف السولوشن غير موجود: {solution_path}")
        else:
            report["solution_size"] = os.path.getsize(solution_path)
            if not solution_path.lower().endswith(SOLUTION_EXTENSIONS):
                report["errors"].append(
                    "امتداد الملف مش .sol أو .solw — اتأكد إنه ملف سولوشن صحيح"
                )

        report["ok"] = not report["errors"]
        return report

    # ------------------------------------------------------------------
    # التحضير: تحميل السولوشن وربط الـ callbacks
    # ------------------------------------------------------------------
    def prepare(
        self,
        assembly_dir: Optional[str] = None,
        solution_path: Optional[str] = None,
    ) -> dict:
        """
        بتتنادى بشكل *متزامن* من ProcessController.start() قبل ما نفتح أي سوكيت،
        عشان أي غلط في المسارات يوقف التشغيل من الأول ويرجع رسالة واضحة.

        بترمي VisionMasterError لو فشلت.
        """
        cfg = _read_config()

        if assembly_dir is None:
            assembly_dir = (cfg.get("assembly_dir") or "").strip() or find_assembly_dir()
        if solution_path is None:
            solution_path = (cfg.get("solution_path") or "").strip()

        # لو فيه handlers قديمة من تشغيلة سابقة نفكّها الأول، وإلا كانت هتتراكم
        # وكل حدث هيتعدّ أكتر من مرة بعد كل Start/Stop.
        self._detach_handlers()

        with self._lock:
            self._assembly_dir = assembly_dir
            self._solution_path = solution_path
            self._last_error = None
            self._running = False
            self._loaded = False

        report = self.check_paths(assembly_dir, solution_path)
        if not report["ok"]:
            msg = " | ".join(report["errors"])
            with self._lock:
                self._last_error = msg
            self._log_add("ERROR", msg)
            raise VisionMasterError(msg)

        try:
            sol_cls = load_vm(assembly_dir)
            self._log_add("INFO", "Assemblies loaded.")

            self._log_add("INFO", f"Loading solution: {solution_path}")
            sol_cls.Load(solution_path, "")
            self._log_add("INFO", f"Loaded successfully: {solution_path}")

            sol = sol_cls.Instance
            info_list = sol.GetAllProcedureList()

            flows: list[tuple[str, object]] = []
            for i in range(info_list.nNum):
                name = info_list.astProcessInfo[i].strProcessName
                flows.append((name, sol[name]))

            if not flows:
                raise VisionMasterError("مفيش فلوهات (Procedures) اتلاقت في السولوشن")

        except VisionMasterError:
            raise
        except Exception as exc:  # noqa: BLE001
            detail = describe_exception(exc)
            with self._lock:
                self._last_error = detail
            self._log_add("ERROR", detail)
            self._log_add("DEBUG", traceback.format_exc())
            raise VisionMasterError(detail) from exc

        with self._lock:
            self._sol_cls = sol_cls
            self._flows = flows
            self._counters = {name: 0 for name, _ in flows}
            self._loaded = True

        self._attach_handlers()
        self._log_add("INFO", f"{len(flows)} flow(s) ready: {[n for n, _ in flows]}")
        return self.status()

    # ------------------------------------------------------------------
    # ربط / فك الـ callbacks
    # ------------------------------------------------------------------
    def _make_handler(self, flow_name: str):
        def on_work_end(*_args):
            with self._lock:
                self._counters[flow_name] = self._counters.get(flow_name, 0) + 1
                count = self._counters[flow_name]
            self._log_add("RUN", f"{flow_name} -> run #{count}")

        return on_work_end

    def _attach_handlers(self):
        with self._lock:
            flows = list(self._flows)
        for name, flow in flows:
            try:
                handler = self._make_handler(name)
                # الاحتفاظ بالمرجع ضروري: من غيره الـ GC بيمسح الـ callback
                self._handlers.append((flow, handler))
                flow.OnWorkEndStatusCallBack += handler
            except Exception as exc:  # noqa: BLE001
                self._log_add("WARNING", f"failed to attach handler for {name}: {exc}", name)

    def _detach_handlers(self):
        for flow, handler in self._handlers:
            try:
                flow.OnWorkEndStatusCallBack -= handler
            except Exception:  # noqa: BLE001
                pass
        self._handlers = []

    # ------------------------------------------------------------------
    # التشغيل
    # ------------------------------------------------------------------
    def run(self) -> dict:
        """ContinuousRunEnable = True لكل الفلوهات. لازم prepare() تكون نجحت قبلها."""
        with self._lock:
            if not self._loaded:
                raise VisionMasterError("prepare() لازم تتنادى قبل run()")
            if self._running:
                return self.status()
            flows = list(self._flows)

        started: list[str] = []
        try:
            for name, flow in flows:
                flow.ContinuousRunEnable = True
                started.append(name)
                self._log_add("INFO", f"[RUNNING] {name}")
        except Exception as exc:  # noqa: BLE001
            detail = describe_exception(exc)
            self._log_add("ERROR", f"failed to start flows: {detail}")
            # رجّع اللي اشتغل عشان ما نسيبش نص تشغيلة
            for name, flow in flows:
                if name in started:
                    try:
                        flow.ContinuousRunEnable = False
                    except Exception:  # noqa: BLE001
                        pass
            with self._lock:
                self._last_error = detail
            raise VisionMasterError(detail) from exc

        with self._lock:
            self._running = True
        self._log_add("INFO", "VisionMaster continuous run started")
        return self.status()

    # ------------------------------------------------------------------
    # الإيقاف
    # ------------------------------------------------------------------
    def stop(self) -> dict:
        """
        إيقاف الفلوهات وفك الـ callbacks.

        *مش* بنعمل Dispose هنا، لأن VmSolution كلاس ساكن والـ .NET assemblies
        مش بتتشال من الـ process — فالـ Dispose وسط التشغيل ممكن يمنع إن Start
        تشتغل تاني بعد Stop. الـ Dispose بيحصل مرة واحدة عند إغلاق التطبيق.
        """
        with self._lock:
            if not self._loaded and not self._running:
                return self.status()
            flows = list(self._flows)
            was_running = self._running
            self._running = False

        if was_running:
            for name, flow in flows:
                try:
                    flow.ContinuousRunEnable = False
                    self._log_add("INFO", f"[STOPPED] {name}")
                except Exception as exc:  # noqa: BLE001
                    self._log_add("ERROR", f"error stopping {name}: {exc}", name)

        self._detach_handlers()

        self._log_add("INFO", "VisionMaster stopped")
        return self.status()

    def dispose(self):
        """Dispose نهائي — بيتنادى عند إغلاق التطبيق."""
        with self._lock:
            sol_cls = self._sol_cls

        self._detach_handlers()

        if sol_cls is not None:
            try:
                sol_cls.Instance.Dispose()
                self._log_add("INFO", "Disposed safely.")
            except Exception as exc:  # noqa: BLE001
                self._log_add("WARNING", f"Dispose: {exc}")

        with self._lock:
            self._sol_cls = None
            self._flows = []
            self._counters = {}
            self._loaded = False
            self._running = False


# نسخة واحدة مشتركة على مستوى التطبيق كله (زي process_control.controller)
controller = VisionMasterController()
