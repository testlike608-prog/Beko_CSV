"""Create user page — FastAPI version of the `CreateUser` blueprint."""

from __future__ import annotations

import csv
import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from ..core import templates

router = APIRouter(tags=["create_user"])

LOGINS_FILE = "logins.csv"


@router.get("/create_user", response_class=HTMLResponse, name="CreateUser.create_user")
async def create_user_page(request: Request):
    if request.session.get("auth") != "admin":
        return PlainTextResponse("Access denied", status_code=403)

    return templates.TemplateResponse(
        request,
        "CREATE_USER_HTML.html",
        {
            "error": "",
            "NewUser_data": {"username": "", "password": "", "auth": ""},
        },
    )


@router.post("/create_user", response_class=HTMLResponse, name="CreateUser.create_user_post")
async def create_user_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    Authentication: str = Form(""),
):
    if request.session.get("auth") != "admin":
        return PlainTextResponse("Access denied", status_code=403)

    username = (username or "").strip()
    password = (password or "").strip()
    auth = (Authentication or "").strip()
    new_user_data = {"username": username, "password": password, "auth": auth}

    if not username or not password or not auth:
        return templates.TemplateResponse(
            request,
            "CREATE_USER_HTML.html",
            {
                "error": "Please fill all fields",
                "NewUser_data": new_user_data,
            },
        )

    with open(LOGINS_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                username,
                password,
                auth,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ]
        )

    return templates.TemplateResponse(
        request,
        "CREATE_USER_HTML.html",
        {
            "message": "User created  successfully!",
            "NewUser_data": new_user_data,
        },
    )
