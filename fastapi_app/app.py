"""
fastapi_app/app.py
------------------
تجميع التطبيق: middleware + static + كل الراوترات.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .core import APP_ROOT, STATIC_DIR, touch_client
from .routers import (
    auth_router,
    create_program_router,
    create_user_router,
    flags_router,
    flash_router,
    home_router,
    io_setting_router,
    manual_router,
    process_router,
    sql_router,
    tests_router,
    time_setting_router,
)

SECRET_KEY = os.environ.get("BEKO_SECRET_KEY", "your-secret-key-here")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Refrigerator Vision System",
        description="Beko production-line vision system API",
        version="2.0.0",
        docs_url="/docs",
        redoc_url=None,
    )

    # بديل flask session
    app.add_middleware(
        SessionMiddleware,
        secret_key=SECRET_KEY,
        session_cookie="beko_session",
        max_age=30 * 24 * 60 * 60,  # 30 يوم (زي Remember Me)
        same_site="lax",
    )

    @app.middleware("http")
    async def _track_client(request: Request, call_next):
        """تسجيل إن فيه متصفح شغال — بيستخدمها main_fastapi عشان ما يفتحش تاب زيادة."""
        if not request.url.path.startswith("/static"):
            touch_client()
        return await call_next(request)

    if os.path.isdir(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # الترتيب مهم: create_program فيه /programs/{filename:path}
    app.include_router(auth_router.router)
    app.include_router(flash_router.router)
    app.include_router(time_setting_router.router)
    app.include_router(home_router.router)
    app.include_router(process_router.router)
    app.include_router(create_program_router.router)
    app.include_router(create_user_router.router)
    app.include_router(sql_router.router)
    app.include_router(manual_router.router)
    app.include_router(io_setting_router.router)
    app.include_router(flags_router.router)
    app.include_router(tests_router.router)

    @app.get("/", include_in_schema=False, name="root")
    async def root():
        return RedirectResponse(url="/login", status_code=303)

    @app.get("/blocked", include_in_schema=False, name="blocked")
    async def blocked(request: Request):
        # main.js بيعمل redirect هنا لو المستخدم فتح الـ DevTools
        return HTMLResponse(
            "<!doctype html><html><head><meta charset='utf-8'><title>Blocked</title></head>"
            "<body style=\"font-family:system-ui;display:flex;align-items:center;"
            "justify-content:center;height:100vh;margin:0;background:#0e1628;color:#e2e8f0\">"
            "<div style='text-align:center'><h1 style='font-size:3rem;margin:0'>&#9888;</h1>"
            "<h2>Access blocked</h2><p style='opacity:.7'>Developer tools are not allowed "
            "in this application.</p><a href='/home' style='color:#0382b8'>Back to dashboard</a>"
            "</div></body></html>",
            status_code=403,
        )

    @app.get("/healthz", include_in_schema=False, name="healthz")
    async def healthz():
        from process_control import controller

        return JSONResponse({"ok": True, "process_running": controller.is_running()})

    @app.on_event("startup")
    async def _startup():
        os.chdir(APP_ROOT)
        os.makedirs("data", exist_ok=True)

        import asyncio

        import db

        # مهم: الاتصال بقواعد البيانات بيتعمل في الخلفية مش هنا.
        # uvicorn مش بيفتح البورت غير لما الـ startup ده يخلص، ولو السيرفرات
        # مش موصولة كل محاولة بتاخد ثواني (والويندوز بيعيد محاولة TCP كمان)،
        # فالواجهة كانت بتفضل مقفولة نص دقيقة. دلوقتي السيرفر بيبقى جاهز فورًا
        # والاتصال بيكمّل ورا، والواجهة بتحدّث حالتها لما يخلص.
        async def _connect_db_background():
            try:
                await asyncio.to_thread(db.auto_connect_db)
            except Exception as exc:  # noqa: BLE001
                print(f"Auto-connect to databases failed: {exc}")

        asyncio.create_task(_connect_db_background())

        import realtime

        realtime.register_handlers()
        realtime.start_tickers()

        print("Web layer ready — press START in the UI to run the process.")

    @app.on_event("shutdown")
    async def _shutdown():
        from process_control import controller

        import realtime

        await realtime.stop_tickers()

        if controller.is_running():
            print("Shutting down: stopping the process...")
            controller.stop()

        # Dispose نهائي لـ VisionMaster هنا بس — مش عند كل Stop.
        # السبب: VmSolution كلاس ساكن والـ .NET assemblies مش بتتشال من الـ
        # process، فالـ Dispose وسط التشغيل ممكن يمنع Start تانية.
        import vision_master

        vision_master.controller.dispose()

    return app


# التطبيق الأصلي (FastAPI) — بيفضل متاح لو حد محتاجه
fastapi_app = create_app()

# لو Socket.IO متسطب، بنغلّف التطبيق بـ ASGIApp عشان يمسك /socket.io/
# وباقي الطلبات تعدي لـ FastAPI زي ما هي. الـ ASGIApp بيمرر الـ lifespan
# للتطبيق اللي جواه، فالـ startup/shutdown events بتشتغل عادي.
import realtime  # noqa: E402

if realtime.is_enabled():
    app = realtime.socketio.ASGIApp(realtime.sio, other_asgi_app=fastapi_app)  # type: ignore[union-attr]
else:
    app = fastapi_app
