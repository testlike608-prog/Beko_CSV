@echo off
REM =====================================================================
REM  Beko Refrigerator Vision System — Nuitka build
REM
REM  بيطلع مجلد واحد في dist\main_fastapi.dist\ تنسخه على جهاز العميل.
REM  بيشتغل native، يعني VisionMaster والترخيص و 127.0.0.1 شغالين
REM  زي ما هما بالظبط — مفيش أي مشاكل كونتينر.
REM
REM  المتطلبات:
REM    pip install nuitka
REM    + كومبايلر C (Nuitka بينزّل MinGW64 لوحده أول مرة،
REM      أو بيستخدم Visual Studio لو متسطب)
REM
REM  أول بناء ممكن ياخد 15-40 دقيقة. اللي بعده أسرع بسبب الكاش.
REM =====================================================================

setlocal
cd /d "%~dp0"

echo.
echo === Building Beko Vision System with Nuitka ===
echo.

python -m nuitka ^
  --standalone ^
  --assume-yes-for-downloads ^
  --output-dir=dist ^
  --company-name="Meeserv" ^
  --product-name="Beko Refrigerator Vision System" ^
  --file-version=2.0.0 ^
  --product-version=2.0.0 ^
  --windows-console-mode=force ^
  --include-data-dir=templates=templates ^
  --include-data-dir=static=static ^
  --include-package=uvicorn ^
  --include-package=socketio ^
  --include-package=engineio ^
  --include-package=clr_loader ^
  --include-package-data=clr_loader ^
  --include-package=pythonnet ^
  --include-module=uvicorn.loops.auto ^
  --include-module=uvicorn.loops.asyncio ^
  --include-module=uvicorn.protocols.http.auto ^
  --include-module=uvicorn.protocols.http.h11_impl ^
  --include-module=uvicorn.protocols.websockets.auto ^
  --include-module=uvicorn.protocols.websockets.websockets_impl ^
  --include-module=uvicorn.lifespan.on ^
  --include-module=engineio.async_drivers.asgi ^
  --nofollow-import-to=tkinter ^
  --nofollow-import-to=pytest ^
  main_fastapi.py

if errorlevel 1 (
  echo.
  echo *** BUILD FAILED ***
  exit /b 1
)

echo.
echo === Build finished ===
echo Output: dist\main_fastapi.dist\
echo.
echo الخطوة الجاية: انسخ الملفات دي جنب main_fastapi.exe
echo   - config.json   (لو مش موجود، التطبيق بيعمل واحد افتراضي)
echo   - logins.csv
echo   - last_db1_settings.txt / last_db2_settings.txt (لو موجودين)
echo   - مجلد data\  (ممكن يبقى فاضي)
echo.
endlocal
