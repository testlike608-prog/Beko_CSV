"""Station status flags — FastAPI version of the `flags` blueprint."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

import ClientsClass as cc
from process_control import controller

router = APIRouter(tags=["flags"])


@router.get("/station_logs/{station}", name="flags.station_logs")
async def station_logs_view(station: int, after: int = 0):
    """مربّع الـ logs اللي تحت كل كارت محطة في الـ Home"""
    import station_logs

    return JSONResponse(station_logs.since(station, after))


@router.get("/station1_status", name="flags.station1_status")
async def station1_status():
    return JSONResponse(
        {
            "arrived": cc.your_s1_arrived_flag,   # True / False
            "result": cc.your_s1_result,          # 'PASS' / 'FAIL' / None
            "failed_tests": getattr(cc, "your_s1_failed_tests", None),
            "dummy_number": cc.your_s1_dummy,     # string أو None
            "sku_number": cc.your_s1_sku,         # string أو None
            "process_running": controller.is_running(),
        }
    )


@router.get("/station2_status", name="flags.station2_status")
async def station2_status():
    return JSONResponse(
        {
            "arrived": cc.your_s2_arrived_flag,
            "result": cc.your_s2_result,
            "failed_tests": getattr(cc, "your_s2_failed_tests", None),
            "dummy_number": cc.your_s2_dummy,
            "sku_number": cc.your_s2_sku,
            "process_running": controller.is_running(),
        }
    )
