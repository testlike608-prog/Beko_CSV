"""
Start / Stop endpoints for the production-line process.

    POST /process/start    -> يشغّل العملية
    POST /process/stop     -> يوقّف العملية
    POST /process/restart  -> stop ثم start
    GET  /process/status   -> حالة العملية (بيستخدمها الـ polling في الواجهة)
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from process_control import controller

from ..core import BOOT_ID

router = APIRouter(prefix="/process", tags=["process"])


def _guard(request: Request):
    """التشغيل والإيقاف متاحين للمستخدم المسجّل دخوله فقط."""
    if not request.session.get("username"):
        return JSONResponse(
            {"ok": False, "message": "Not authenticated"}, status_code=401
        )
    return None


#
# ملحوظة: الراوتس دي معرّفة بـ `def` مش `async def` عن قصد.
# FastAPI بيشغّل الـ sync endpoints في threadpool، وده مهم لأن
# start() بتحمّل VisionMaster (.NET) بشكل بلوكنج — لو كانت async كانت
# هتقفل الـ event loop بتاع الويب وتوقف باقي الـ requests.
# (العملية نفسها بتشتغل على loop تاني منفصل — شوف async_runtime.py)
#

@router.get("/status", name="process.status")
def process_status():
    # boot_id بيتغيّر مع كل تشغيلة للسيرفر — الواجهة بتستخدمه
    # عشان تعمل reload لنفسها بعد إعادة التشغيل بدل فتح تاب جديد.
    return JSONResponse({**controller.status(), "boot_id": BOOT_ID})


@router.post("/start", name="process.start")
def process_start(request: Request):
    denied = _guard(request)
    if denied is not None:
        return denied

    result = controller.start()
    result["status"] = controller.status()
    return JSONResponse(result, status_code=200 if result["ok"] else 409)


@router.post("/stop", name="process.stop")
def process_stop(request: Request):
    denied = _guard(request)
    if denied is not None:
        return denied

    # بيرجع فورًا — الإيقاف بيكمّل في الخلفية والحالة بتتبعت للواجهة
    result = controller.request_stop()
    result["status"] = controller.status()
    return JSONResponse(result, status_code=200 if result["ok"] else 409)


@router.post("/restart", name="process.restart")
def process_restart(request: Request):
    denied = _guard(request)
    if denied is not None:
        return denied

    result = controller.request_restart()
    result["status"] = controller.status()
    return JSONResponse(result, status_code=200 if result["ok"] else 409)
