"""
fastapi_app/core.py
-------------------
الحاجات المشتركة بين كل الراوترات: مسار المشروع، محرك القوالب، والـ session helpers.

ملحوظة مهمة عن url_for:
    القوالب القديمة بتستخدم {{ url_for('home.page_index') }} بنفس أسماء الـ Flask blueprints.
    عشان كده كل route في FastAPI متسمّي بنفس الاسم بالظبط (name="home.page_index")
    فالقوالب شغالة زي ما هي من غير أي تعديل.
"""

from __future__ import annotations

import os
import sys
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates


# ----------------------------------------------------------------------
# مسارين مختلفين، مش مسار واحد
#
# في وضع onefile الـ bootstrap بيفك ضغط البرنامج في مكان مؤقت وبيشغله
# من هناك. توثيق Nuitka بيقول بالنص:
#
#     sys.argv[0] will be the original executable path, whereas __file__
#     will be the temporary or permanent path the bootstrap executable
#     unpacks to. Data files will be in the later location; your original
#     environment files will be in the former location.
#
# يعني:
#   BUNDLE_ROOT = جوه الحزمة    -> templates و static (بنقرا منهم بس)
#   APP_ROOT    = جنب الـ exe   -> config.json و logins.csv و CreateProgram
#                                  و data/ و last_db*_settings.txt (بنكتب فيهم)
#
# في وضع standalone الاتنين نفس المكان، فالكود ده مبيغيّرش أي سلوك حالي.
# لو خلطناهم في onefile، إعدادات العميل هتتكتب في فولدر مؤقت وتتمسح
# أول ما البرنامج يقفل — من غير أي رسالة خطأ.
# ----------------------------------------------------------------------
def _bundle_directory() -> str:
    """مكان الملفات المرفقة مع البرنامج. __file__ بيشتغل صح في الوضعين."""
    return os.path.normpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _application_directory() -> str:
    """
    مكان ملفات المستخدم — لازم يفضل ثابت بين التشغيلات.

    __compiled__.containing_dir هو اللي Nuitka بيرشحه للحالة دي، وبيشتغل
    مع standalone و onefile الاتنين. مش موجود وقت التشغيل العادي من
    السورس، عشان كده الـ NameError متوقع ومتعالج.
    """
    try:
        return os.path.normpath(__compiled__.containing_dir)  # type: ignore[name-defined]  # noqa: F821
    except NameError:
        pass

    # PyInstaller — مش مستخدم حاليًا بس سيبناه للأمان
    if getattr(sys, "frozen", False):
        return os.path.normpath(os.path.dirname(sys.executable))

    return _bundle_directory()


BUNDLE_ROOT = _bundle_directory()
APP_ROOT = _application_directory()

TEMPLATES_DIR = os.path.join(BUNDLE_ROOT, "templates")
STATIC_DIR = os.path.join(BUNDLE_ROOT, "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ----------------------------------------------------------------------
# Cache busting للملفات الساكنة
#
# Starlette.StaticFiles بيبعت etag و last-modified بس من غير Cache-Control،
# فالمتصفح بيطبّق "heuristic caching" وممكن يستخدم نسخة قديمة من main.js
# من غير ما يسأل السيرفر. والقوالب بتتعمل render كل مرة، فكنا بنطلع
# HTML جديد مع JS قديم — وده بيخلي أي زرار جديد يبان وكأنه مش شغال.
#
# الحل: نضيف ?v=<وقت آخر تعديل> فالمتصفح يجيب نسخة جديدة أول ما الملف يتغيّر.
# ----------------------------------------------------------------------
def static_version(filename: str) -> str:
    try:
        return str(int(os.path.getmtime(os.path.join(STATIC_DIR, filename))))
    except OSError:
        return "0"


def static_exists(filename: str) -> bool:
    """
    عشان ما نطلبش ملف مش موجود ونجيب 404 في اللوج.
    مستخدمة مع socket.io.min.js لأنه بيتحط يدويًا (جهاز أوفلاين).
    """
    return os.path.isfile(os.path.join(STATIC_DIR, filename))


templates.env.globals["static_v"] = static_version
templates.env.globals["static_exists"] = static_exists


# ----------------------------------------------------------------------
# إعادة استخدام نفس التاب بعد إعادة تشغيل السيرفر
#
# BOOT_ID بيتغيّر مع كل تشغيلة. الصفحة بتقارن الـ id اللي شافته أول مرة
# باللي راجع دلوقتي — لو اتغيّر يبقى السيرفر اتقفل واشتغل تاني، فتعمل
# reload لنفسها بدل ما نفتح تاب جديد.
#
# و touch_client() بتسجّل آخر مرة أي متصفح كلّم السيرفر، عشان main_fastapi
# يعرف إن فيه تاب مفتوح أصلاً وما يفتحش واحد جديد.
# ----------------------------------------------------------------------
BOOT_ID = uuid.uuid4().hex

_last_client_seen = 0.0


def touch_client() -> None:
    global _last_client_seen
    _last_client_seen = time.time()


def client_seen_within(seconds: float) -> bool:
    return _last_client_seen > 0 and (time.time() - _last_client_seen) <= seconds


# ----------------------------------------------------------------------
# Session helpers (بديل flask.session)
# ----------------------------------------------------------------------
def get_session(request: Request) -> dict:
    return request.session


def current_user(request: Request):
    return request.session.get("username")


def current_auth(request: Request):
    return request.session.get("auth")


def require_login(request: Request):
    """
    بديل الـ @login_required decorator.
    بترجع None لو المستخدم مسجّل دخول، أو RedirectResponse لصفحة اللوجين.
    """
    if not request.session.get("username"):
        return RedirectResponse(url="/login", status_code=303)
    return None


# ----------------------------------------------------------------------
# صلاحيات (auth = "dev" | "admin" | "user")
# ----------------------------------------------------------------------
DEV_ROLE = "dev"
ADMIN_ROLES = ("dev", "admin")


def is_dev(request: Request) -> bool:
    return request.session.get("auth") == DEV_ROLE


def is_admin(request: Request) -> bool:
    return request.session.get("auth") in ADMIN_ROLES


def require_dev(request: Request):
    """
    حارس للـ JSON endpoints المتاحة لوضع الـ Developer بس.
    بترجع None لو مسموح، أو JSONResponse بالخطأ لو ممنوع.

    ملحوظة: إخفاء الزرار في القالب مجرد CSS — المنع الحقيقي هنا.
    """
    if not request.session.get("username"):
        return JSONResponse(
            {"ok": False, "message": "Not authenticated"}, status_code=401
        )
    if not is_dev(request):
        return JSONResponse(
            {"ok": False, "message": "Developer access required"}, status_code=403
        )
    return None


def redirect(url: str, status_code: int = 303) -> RedirectResponse:
    """redirect افتراضي بـ 303 عشان POST -> GET يشتغل صح."""
    return RedirectResponse(url=url, status_code=status_code)
