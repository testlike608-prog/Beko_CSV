"""SQL connection page + status — FastAPI version of the `SQL` blueprint."""

from __future__ import annotations

from typing import Optional

import pyodbc
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

import db
from helpers import TIME_SETTINGS
from ..core import templates

router = APIRouter(tags=["sql"])


# pyodbc بيعمل blocking، فالراوتس دي sync عشان FastAPI يشغّلها في threadpool
@router.get("/sql_status", name="SQL.http_sql_status")
def http_sql_status():
    """Get SQL connection status for AJAX updates"""
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

    return JSONResponse({"db1_connected": db1_connected, "db2_connected": db2_connected})


@router.get("/sql_connection", response_class=HTMLResponse, name="SQL.sql_connection")
async def sql_connection_page(request: Request):
    return templates.TemplateResponse(
        request,
        "SQL_CONNECTION_HTML.html",
        {
            "message": "",
            "form_data": {},
            "conn_str_db1_global": db.conn_str_db1_global,
            "conn_str_db2_global": db.conn_str_db2_global,
        },
    )


@router.post("/sql_connection", response_class=HTMLResponse, name="SQL.sql_connection_post")
def sql_connection_submit(
    request: Request,
    action: Optional[str] = Form(None),
    reset: Optional[str] = Form(None),
    server_addr1: Optional[str] = Form(None),
    database1: Optional[str] = Form(None),
    server_addr2: Optional[str] = Form(None),
    database2: Optional[str] = Form(None),
    Authentication: Optional[str] = Form(None),
    login: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
):
    message = ""

    # If Reset button pressed
    if reset == "true":
        return templates.TemplateResponse(
            request,
            "SQL_CONNECTION_HTML.html",
            {
                "message": "",
                "form_data": {},
                "conn_str_db1_global": db.conn_str_db1_global,
                "conn_str_db2_global": db.conn_str_db2_global,
            },
        )

    form_data = {
        "action": action,
        "server_addr1": server_addr1,
        "database1": database1,
        "server_addr2": server_addr2,
        "database2": database2,
        "Authentication": Authentication,
        "login": login,
        "password": password,
    }

    # DATABASE CONNECTION
    if action == "db":
        try:
            # بنستخدم أحسن درايفر متاح على الجهاز بدل ما نفترض 18 دايمًا
            conn_str1 = db.build_conn_str(
                server_addr1, database1, Authentication, login, password
            )
            conn_str2 = db.build_conn_str(
                server_addr2, database2, Authentication, login, password
            )

            # Test both connections separately
            pyodbc.connect(conn_str1, timeout=TIME_SETTINGS["dbTimeout"]).close()
            pyodbc.connect(conn_str2, timeout=TIME_SETTINGS["dbTimeout"]).close()

            db.conn_str_db1_global = conn_str1
            db.conn_str_db2_global = conn_str2
            message = "DATABASE CONNECTION SUCCESSFUL (Server 1 & Server 2)"

            with open("last_db1_settings.txt", "w") as f:
                f.write(f"{server_addr1}|{database1}|{Authentication}|{login}|{password}")

            with open("last_db2_settings.txt", "w") as f:
                f.write(f"{server_addr2}|{database2}|{Authentication}|{login}|{password}")

        except Exception as ex:  # noqa: BLE001
            message = f"Database connection failed: {ex}"

    return templates.TemplateResponse(
        request,
        "SQL_CONNECTION_HTML.html",
        {
            "message": message,
            "form_data": form_data,
            "conn_str_db1_global": db.conn_str_db1_global,
            "conn_str_db2_global": db.conn_str_db2_global,
        },
    )
