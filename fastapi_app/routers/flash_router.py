"""Splash / loading page — FastAPI version of the `flash` blueprint."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..core import templates

router = APIRouter(tags=["flash"])


@router.get("/loading", response_class=HTMLResponse, name="flash.loading")
async def loading(request: Request):
    return templates.TemplateResponse(request, "page_splash_HTML.html", {})
