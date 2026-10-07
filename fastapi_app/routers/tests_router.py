"""
Endpoints كانت ناقصة: الواجهة (static/main.js) بتناديهم لكن مكانش ليهم
راوت في السيرفر، فكانوا بيرجعوا 404.

    POST /reset_error   -> resetErrorCondition()  في main.js
    POST /delete_test   -> deleteTest(name)       في main.js
    POST /reset_tests   -> resetDefaults()        في main.js
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import ClientsClass as cc
from helpers import load_tests, save_tests

router = APIRouter(tags=["tests"])


@router.post("/reset_error", name="tests.reset_error")
def reset_error():
    """تصفير حالة الخطأ في المحطات وإطفاء الأجراس."""
    try:
        cc.NO_CSV_ERROR = False
        cc.NO_CSV_ERROR2 = False
        cc.Buzzer_Flag_to_OFF = True
        cc.Buzzer_Flag_to_OFF2 = True
        cc.Manual_Scanner_MODE = False
        cc.Manual_Scanner_MODE2 = False
        cc.your_s1_result = None
        cc.your_s2_result = None
        print("Error condition reset")
        return JSONResponse({"ok": True, "msg": "Error condition reset"})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@router.post("/delete_test", name="tests.delete_test")
async def delete_test(request: Request):
    """حذف اختبار واحد بالاسم من tests.json"""
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        payload = {}

    name = (payload or {}).get("name")
    if not name:
        return JSONResponse({"ok": False, "msg": "No test name provided"}, status_code=400)

    try:
        tests = load_tests()
        remaining = [t for t in tests if t.get("name") != name]

        if len(remaining) == len(tests):
            return JSONResponse({"ok": False, "msg": f"Test '{name}' not found"}, status_code=404)

        save_tests(remaining)
        print(f"Test deleted: {name}")
        return JSONResponse({"ok": True, "msg": f"Test '{name}' deleted", "count": len(remaining)})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@router.post("/reset_tests", name="tests.reset_tests")
def reset_tests():
    """مسح كل الاختبارات الديناميكية من tests.json"""
    try:
        save_tests([])
        print("All dynamic tests cleared")
        return JSONResponse({"ok": True, "msg": "All tests cleared"})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)
