"""Login / logout — FastAPI version of the `auth` Flask blueprint."""

from __future__ import annotations

import csv
import os
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from ..core import redirect, templates

router = APIRouter(tags=["auth"])

LOGINS_FILE = "logins.csv"

# ----------------- التأكد من وجود logins.csv -----------------
if not os.path.exists(LOGINS_FILE):
    with open(LOGINS_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Username", "Password", "Authentication"])


def check_credentials(username: str, password: str) -> Optional[str]:
    """نفس منطق الـ Flask بالظبط."""
    if os.path.exists(LOGINS_FILE):
        with open(LOGINS_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                u = row.get("username") or row.get("Username") or row.get("USER") or ""
                p = row.get("password") or row.get("Password") or ""
                auth = row.get("auth") or row.get("Auth") or row.get("Authentication") or ""

                if u == username and p == password:
                    return auth

    if username == "M.Ashraf" and password == "Beko2026":
        return "admin"
    if username == "Meeserv" and password == "meeserv@2026":
        return "dev"

    return None


@router.get("/login", response_class=HTMLResponse, name="auth.login")
async def login_page(request: Request):
    # الدخول على /login بيعمل logout ضمنيًا زي ما الواجهة متوقعة
    request.session.clear()
    return templates.TemplateResponse(request, "LOGIN_HTML.html", {"error": None})


@router.post("/login", response_class=HTMLResponse, name="auth.login_post")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: Optional[str] = Form(None),
):
    auth = check_credentials(username, password)

    if auth:
        request.session["username"] = username
        request.session["auth"] = auth
        request.session["permanent"] = bool(remember_me)
        return redirect("/loading")

    return templates.TemplateResponse(
        request,
        "LOGIN_HTML.html",
        {"error": "Invalid username or password"},
    )


@router.get("/logout", name="auth.logout")
async def logout(request: Request):
    request.session.clear()
    return redirect("/login")
