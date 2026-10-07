"""Index page + manual queue endpoints — FastAPI version of the `home` blueprint."""

from __future__ import annotations

import os
import queue as queue_mod

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

import ClientsClass as cc
import helpers as hlb
from ..core import redirect, templates

router = APIRouter(tags=["home"])


@router.post("/home/add_to_queue", name="home.add_to_queue")
async def add_to_queue(request: Request):
    data = await request.json()
    dummy_number = data.get("dummy_number")

    if not dummy_number:
        return JSONResponse({"status": "error", "message": "No data"}, status_code=400)

    try:
        cc.queue_manual_FOR_FAILURE.put(dummy_number)
        cc.queue_manual_FOR_Proessing.put(dummy_number)

        return JSONResponse(
            {"status": "success", "current_count": cc.queue_manual_FOR_FAILURE.qsize()},
            status_code=200,
        )
    except queue_mod.Full:
        return JSONResponse({"status": "error", "message": "Queue is full!"}, status_code=500)


@router.post("/home/add_to_queue2", name="home.add_to_queue2")
async def add_to_queue2(request: Request):
    data = await request.json()
    dummy_number = data.get("dummy_number")

    if not dummy_number:
        return JSONResponse({"status": "error", "message": "No data"}, status_code=400)

    try:
        cc.queue_manual2_FOR_FAILURE.put(dummy_number, block=False)
        cc.queue_manual2_FOR_Proessing.put(dummy_number, block=False)
        cc.is_waiting2 = False
        cc.Manual_Scanner_MODE2 = False

        return JSONResponse(
            {"status": "success", "current_count": cc.queue_manual2_FOR_FAILURE.qsize()},
            status_code=200,
        )
    except queue_mod.Full:
        return JSONResponse({"status": "error", "message": "Queue is full!"}, status_code=500)


@router.get("/home", response_class=HTMLResponse, name="home.page_index")
async def page_index(request: Request):
    if not request.session.get("username"):
        return redirect("/login")

    csv_files = []
    if os.path.isdir(hlb.CSV_SOURCE_DIR):
        for file in os.listdir(hlb.CSV_SOURCE_DIR):
            if file.endswith(".csv"):
                file_path = os.path.join(hlb.CSV_SOURCE_DIR, file)
                if os.path.isfile(file_path):
                    csv_files.append(
                        {
                            "name": file,
                            "path": f"/programs/{file}",
                            "size": os.path.getsize(file_path),
                        }
                    )

        csv_files.sort(
            key=lambda x: os.path.getmtime(os.path.join(hlb.CSV_SOURCE_DIR, x["name"])),
            reverse=True,
        )

    return templates.TemplateResponse(
        request,
        "INDEX_HTML.html",
        {
            "username": request.session.get("username"),
            "auth": request.session.get("auth"),
            "csv_files": csv_files,
        },
    )
