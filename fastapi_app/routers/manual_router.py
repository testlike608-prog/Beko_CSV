"""Manual scanner / no-CSV popups — FastAPI version of the `Manual` blueprint."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

import ClientsClass as cc
from ..core import redirect, templates

router = APIRouter(tags=["manual"])


@router.get("/ManualPopup", response_class=HTMLResponse, name="Manual.page_ManualPopup")
async def page_manual_popup(request: Request):
    return templates.TemplateResponse(
        request,
        "Manual_HTML.html",
        {"message": "ERROR : Auto SCANNING FAILED"},
    )


@router.get("/NoCSV", name="Manual.page_CSVPopup")
async def page_csv_popup(request: Request):
    if cc.NO_CSV_ERROR:
        return templates.TemplateResponse(
            request,
            "NOCSV_HTML.html",
            {"message": "ERROR : NO CSV FILE FOUND"},
        )
    return redirect("/home")


@router.post("/ManualPopup/ack", name="Manual.manual_popup_ack")
async def manual_popup_ack():
    cc.Buzzer_Flag_to_OFF = True
    cc.Manual_Scanner_MODE = False  # الفلاج بيتقفل هنا
    return redirect("/home")


@router.post("/NoCSV/ack", name="Manual.csv_popup_ack")
async def csv_popup_ack():
    cc.Buzzer_Flag_to_OFF2 = True
    cc.NO_CSV_ERROR = False  # يقفل الفلاج
    return redirect("/home")


@router.get("/check-flags", name="Manual.check_flags")
async def check_flags():
    cc.Buzzer_Flag_to_OFF = False
    return JSONResponse(
        {
            "manual_scanner": cc.Manual_Scanner_MODE,
            "no_csv_error": cc.NO_CSV_ERROR,
            "no_csv_file": getattr(cc, "NO_CSV_FILE", None),
            "scan_skipped": getattr(cc, "SCAN_SKIPPED", False),
            "scan_skipped_count": getattr(cc, "SCAN_SKIPPED_COUNT", 0),
        }
    )


@router.get("/check-flags2", name="Manual.check_flags2")
async def check_flags2():
    cc.Buzzer_Flag_to_OFF = False
    return JSONResponse(
        {
            "manual_scanner": cc.Manual_Scanner_MODE2,
            "no_csv_error": cc.NO_CSV_ERROR2,
            "no_csv_file": getattr(cc, "NO_CSV_FILE2", None),
            "scan_skipped": getattr(cc, "SCAN_SKIPPED2", False),
            "scan_skipped_count": getattr(cc, "SCAN_SKIPPED_COUNT2", 0),
        }
    )


@router.post("/api/station", name="Manual.handle_station_data")
async def handle_station_data(request: Request):
    payload = await request.json()
    data_received = payload.get("station_data")

    if data_received:
        cc.queue_manual_FOR_FAILURE.put(data_received)
        cc.queue_manual_FOR_Proessing.put(data_received)
        cc.is_waiting = False
        cc.Manual_Scanner_MODE = False

        return JSONResponse(
            {"status": "success", "message": "تم إضافة الداتا وتغيير المتغير"}, status_code=200
        )

    return JSONResponse(
        {"status": "error", "message": "لم يتم استلام أي بيانات"}, status_code=400
    )


@router.post("/api/station2", name="Manual.handle_station_data2")
async def handle_station_data2(request: Request):
    payload = await request.json()
    data_received = payload.get("station_data")

    if data_received:
        cc.queue_manual2_FOR_FAILURE.put(data_received)
        cc.queue_manual2_FOR_Proessing.put(data_received)
        cc.is_waiting2 = False
        cc.Manual_Scanner_MODE2 = False

        return JSONResponse(
            {"status": "success", "message": "تم إضافة الداتا وتغيير المتغير"}, status_code=200
        )

    return JSONResponse(
        {"status": "error", "message": "لم يتم استلام أي بيانات"}, status_code=400
    )


@router.post("/control", name="Manual.control")
async def control():
    try:
        cc.NO_CSV_ERROR = False
        cc.NO_CSV_FILE = None
        cc.Buzzer_Flag_to_OFF = True
        return JSONResponse({"status": "success"}, status_code=200)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/control2", name="Manual.control2")
async def control2():
    try:
        cc.NO_CSV_ERROR2 = False
        cc.NO_CSV_FILE2 = None
        cc.Buzzer_Flag_to_OFF = True
        return JSONResponse({"status": "success"}, status_code=200)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ----------------------------------------------------------------------
# Scan-skipped alerts (Manual mode = OFF)
#
# لما الـ Manual mode يكون مقفول، السكان الفاشل مش بيفتح popup ولا بيرن
# بازر — بيتسجّل فلاج هنا بس، والواجهة بتعرضه في جرس الـ Alerts.
# ----------------------------------------------------------------------
@router.post("/scan_skipped/ack", name="Manual.scan_skipped_ack")
async def scan_skipped_ack():
    cc.SCAN_SKIPPED = False
    cc.SCAN_SKIPPED_COUNT = 0
    return JSONResponse({"status": "success"})


@router.post("/scan_skipped2/ack", name="Manual.scan_skipped_ack2")
async def scan_skipped_ack2():
    cc.SCAN_SKIPPED2 = False
    cc.SCAN_SKIPPED_COUNT2 = 0
    return JSONResponse({"status": "success"})
