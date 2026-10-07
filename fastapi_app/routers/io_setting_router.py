"""
I/O mapping — FastAPI version of the `io_mapping` blueprint.

كل الـ endpoints دي متاحة لوضع الـ Developer بس (auth == "dev").
قبل كده كانت مفتوحة تمامًا من غير أي تحقق، رغم إن الزرار في الواجهة
كان مخفي — والإخفاء ده مجرد CSS وسهل تخطيه.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import ioSetting
import vision_master
from ioSetting import (
    generate_modbus_command,
    get_vision_master_config,
    save_mapping_to_file,
    save_vision_master_config,
)

from ..core import require_dev

router = APIRouter(tags=["io_mapping"])


# ----------------------------------------------------------------------
# I/O mapping
# ----------------------------------------------------------------------
@router.get("/mapping", name="io_mapping.get_mapping")
async def get_mapping(request: Request):
    """قراءة الماپينج الحالي (بتستخدمها المودال في الواجهة)."""
    denied = require_dev(request)
    if denied is not None:
        return denied
    return JSONResponse(ioSetting.io_mapping)


@router.post("/save_mapping", name="io_mapping.save_mapping")
async def save_mapping(request: Request):
    denied = require_dev(request)
    if denied is not None:
        return denied

    payload = await request.json()

    # نقبل الأرقام بس — أي حقل تاني ممكن يفسد generate_modbus_command
    clean = {}
    for key, value in (payload or {}).items():
        try:
            clean[key] = int(value)
        except (TypeError, ValueError):
            return JSONResponse(
                {"status": "error", "message": f"Invalid pin value for '{key}'"},
                status_code=400,
            )

    ioSetting.io_mapping.update(clean)
    save_mapping_to_file()
    return JSONResponse({"status": "success"})


# ----------------------------------------------------------------------
# خصائص التشغيل (features) — Manual Scanner mode ON/OFF
#
# GET مفتوح لأي مستخدم مسجّل (الواجهة بتعرض الحالة)، أما الحفظ فـ dev بس.
# ----------------------------------------------------------------------
@router.get("/features", name="io_mapping.get_features")
async def get_features(request: Request):
    return JSONResponse(ioSetting.get_features())


@router.post("/features", name="io_mapping.save_features")
async def save_features(request: Request):
    denied = require_dev(request)
    if denied is not None:
        return denied

    payload = await request.json()
    saved = ioSetting.save_features(payload or {})
    return JSONResponse({"status": "success", "features": saved})


# ----------------------------------------------------------------------
# عناوين الأجهزة (IP / Port) — Developer mode فقط
#
# قبل كده كانت متكتوبة بإيد في ClientsClass.py، فتغيير IP كان محتاج
# إعادة بناء الـ exe. دلوقتي بتتحفظ في config.json وبتتطبق مع Restart.
# ----------------------------------------------------------------------
@router.get("/endpoints", name="io_mapping.get_endpoints")
async def get_endpoints(request: Request):
    denied = require_dev(request)
    if denied is not None:
        return denied

    return JSONResponse(
        {
            "endpoints": ioSetting.get_endpoints(),
            "labels": ioSetting.ENDPOINT_LABELS,
            "defaults": ioSetting.default_endpoints,
        }
    )


@router.post("/endpoints", name="io_mapping.save_endpoints")
async def save_endpoints(request: Request):
    denied = require_dev(request)
    if denied is not None:
        return denied

    payload = await request.json()

    try:
        saved = ioSetting.save_endpoints(payload or {})
    except ValueError as exc:
        # عنوان غلط بيوقّف الخط كله، فبنرفض الحفظ ونوري المستخدم السبب
        # بدل ما المشكلة تظهر وقت Start.
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)

    return JSONResponse(
        {
            "status": "success",
            "endpoints": saved,
            "message": "Saved — press Restart to apply.",
        }
    )


@router.post("/endpoints/reset", name="io_mapping.reset_endpoints")
async def reset_endpoints(request: Request):
    denied = require_dev(request)
    if denied is not None:
        return denied

    return JSONResponse({"status": "success", "endpoints": ioSetting.reset_endpoints()})


@router.post("/command", name="io_mapping.execute_command")
async def execute_command(request: Request):
    denied = require_dev(request)
    if denied is not None:
        return denied

    data = await request.json()
    func_name = data.get("function")
    action = data.get("action")

    hex_command = generate_modbus_command(func_name, action)

    return JSONResponse({"command": hex_command})


@router.post("/off_all", name="io_mapping.off_all")
async def off_all(request: Request):
    denied = require_dev(request)
    if denied is not None:
        return denied

    cmd_off_all = "000100000009010F00000010020000"
    return JSONResponse({"command": cmd_off_all, "status": "All Off Sent"})


# ----------------------------------------------------------------------
# مسارات VisionMaster (Developer mode فقط)
# ----------------------------------------------------------------------
@router.get("/vision_master/paths", name="io_mapping.get_vision_paths")
async def get_vision_paths(request: Request):
    denied = require_dev(request)
    if denied is not None:
        return denied

    cfg = get_vision_master_config()
    detected_assembly = vision_master.find_assembly_dir()

    return JSONResponse(
        {
            **cfg,
            # اقتراحات تظهر كـ placeholder لو الحقول فاضية
            "detected_assembly_dir": detected_assembly,
            "detected_solution_path": vision_master.default_solution_guess(),
            "check": vision_master.VisionMasterController.check_paths(
                (cfg.get("assembly_dir") or "").strip() or detected_assembly,
                (cfg.get("solution_path") or "").strip(),
            ),
        }
    )


@router.post("/vision_master/paths", name="io_mapping.save_vision_paths")
async def save_vision_paths(request: Request):
    denied = require_dev(request)
    if denied is not None:
        return denied

    payload = await request.json()
    cfg = save_vision_master_config(payload or {})

    assembly_dir = (cfg.get("assembly_dir") or "").strip() or vision_master.find_assembly_dir()
    check = vision_master.VisionMasterController.check_paths(
        assembly_dir, (cfg.get("solution_path") or "").strip()
    )

    # بنحفظ حتى لو المسار غلط عشان المستخدم يقدر يكمّل تعديل،
    # بس بنرجّع نتيجة الفحص عشان الواجهة تحذّره قبل ما يضغط START.
    return JSONResponse({"status": "success", "config": cfg, "check": check})


@router.get("/vision_master/browse", name="io_mapping.vision_browse")
async def vision_browse(request: Request, path: str = "", only_dirs: bool = False):
    """
    تصفّح ملفات الجهاز اللي شغال عليه التطبيق (Developer mode فقط).
    بتستخدمها نافذة الـ Browse عشان تختار مجلد الاسمبلي أو ملف السولوشن.
    """
    denied = require_dev(request)
    if denied is not None:
        return denied

    return JSONResponse(vision_master.browse_directory(path, only_dirs=only_dirs))


@router.get("/vision_master/status", name="io_mapping.vision_status")
async def vision_status(request: Request):
    denied = require_dev(request)
    if denied is not None:
        return denied

    return JSONResponse(
        {
            "status": vision_master.controller.status(),
            "logs": vision_master.controller.logs(limit=100),
        }
    )
