"""Time settings — FastAPI version of the `time_settings` blueprint."""

from __future__ import annotations

import json
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["time_settings"])

SETTINGS_FILE = "time_settings.json"

DEFAULT_SETTINGS = {
    "deviceConnectTimeout": 5.0,
    "deviceRecvTimeout": 1.0,
    "clientSocketTimeout": 1.0,
    "reconnectBaseDelay": 0.5,
    "maxBackoff": 30,
    "reconnectCheckInterval": 1,
    "defaultCharDelay": 100,
    "s1CharDelay": 100,
    "s2CharDelay": 100,
    "frameDelay": 1,
    "followupDelay": 30,
    "statusRefresh": 1500,
    "logPolling": 800,
    "server4Refresh": 2000,
    "sendTimeout": 25,
    "autoSendGap": 120,
    "dbTimeout": 10,
    "ImageTimeout": 10,
    "PlcSignal": 0.1,
    "duplicateScanWindow": 120,
}


@router.get("/time_settings", name="time_settings.get_time_settings")
async def get_time_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
            return JSONResponse({"ok": True, "settings": settings})
        return JSONResponse({"ok": True, "settings": DEFAULT_SETTINGS})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "msg": str(e)})


@router.post("/time_settings", name="time_settings.save_time_settings")
async def save_time_settings(request: Request):
    try:
        data = await request.json()
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return JSONResponse({"ok": True})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "msg": str(e)})
