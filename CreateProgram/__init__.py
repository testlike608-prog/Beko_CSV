from flask import Blueprint
from flask import render_template, redirect, url_for
from flask import Flask, request, jsonify, render_template_string, send_from_directory, session
from typing import Dict,Tuple,List
import os,re
import helpers as hlb
from helpers import _save_csv_file,_csv_path,load_tests,save_tests
import ClientsClass as cc
import csv

# ----------------------------------------------------------------------
# مجلد البرامج = <مكان الـ exe>\Programs
#
# مصدر واحد للمسار ده هو helpers.CSV_SOURCE_DIR — قبل كده الملف ده كان
# بيحسب المسار لوحده، فكان سهل إن الاتنين يفترقوا ونبقى بنكتب في مكان
# وبنقرا من مكان تاني. helpers كمان هي اللي بتعمل الفولدر وبتنقل
# الملفات القديمة من CreateProgram\، فمفيش داعي نكرر ده هنا.
#
# الاسم القديم للفولدر كان "CreateProgram" — نفس اسم الحزمة دي بالظبط،
# وده كان بيلخبط الكود بالداتا. بقى "Programs".
# ----------------------------------------------------------------------
PROGRAMS_DIR = hlb.CSV_SOURCE_DIR

#Globals
CSV_CACHE: Dict[Tuple[str, str], Dict] = {}
CSV_CACHE_MAX = 256
CreateProgram = Blueprint("CreateProgram", 
    __name__,
    static_folder="static",
    template_folder="templates"
)


# ---------------- CSV Functions ----------------
def _csv_path(sku: str, part: str) -> str:
    safe_sku = re.sub(r'[^\w\-]', '', sku or "")
    return os.path.join(PROGRAMS_DIR, f"{safe_sku}{part}.csv")

def _load_csv_file(path: str) -> Dict[str, str]:
    out = {}
    with open(path, "r", newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            if len(row) == 2:
                out[row[0]] = row[1]
    return out

def _save_csv_file(path: str, rows: List[Tuple[str, str]], append: bool = False):
    """
    يكتب الصفوف في ملف CSV.

    append=False  -> يكتب الملف من الأول (مع صف العناوين).
    append=True   -> يضيف الصفوف في آخر الملف من غير ما يكرر العناوين.
                     لو الملف مش موجود أو فاضي بيكتب العناوين الأول.

    ملحوظة: البارامتر ده كان ناقص، وكان أي استدعاء بـ append=True
    بيرمي TypeError وبيتبلع في الـ try/except — فالاختبارات الديناميكية
    كانت بتضيع ومتتحفظش في ملفات الـ CSV.
    """
    mode = "a" if append else "w"
    need_header = True

    # حزام أمان: لو الفولدر اتمسح وهو شغال، أو لو المسار جاي من مكان
    # تاني، بنعمله قبل الكتابة بدل ما نقع في FileNotFoundError.
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    if append:
        try:
            need_header = (not os.path.isfile(path)) or os.path.getsize(path) == 0
        except OSError:
            need_header = True

    with open(path, mode, newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if need_header:
            w.writerow(["Label", "Value"])
        for k, v in rows:
            w.writerow([k, v])

def _get_label(val: str) -> str:
    """Extract label from 'Label|Code' format"""
    if not val:
        return ""
    parts = str(val).split("|", 1)
    return parts[0].strip() if len(parts) == 2 else val

def _get_code(val: str) -> str:
    """Extract code from 'Label|Code' format"""
    if not val:
        return ""
    parts = str(val).split("|", 1)
    return parts[1].strip() if len(parts) == 2 else ""

def get_program_cached(sku: str, part: str):
    part = (part or "").upper()
    if part not in ("S1", "S2"):
        raise FileNotFoundError("part must be S1 or S2")
    path = _csv_path(sku, part)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{os.path.basename(path)} not found")
    mtime = os.path.getmtime(path)
    key = (sku, part)
    e = CSV_CACHE.get(key)
    if e and e.get("mtime") == mtime:
        return e
    if len(CSV_CACHE) > CSV_CACHE_MAX:
        victim = sorted(CSV_CACHE.items(), key=lambda kv: kv[1].get("mtime", 0.0))[0][0]
        CSV_CACHE.pop(victim, None)
    data = _load_csv_file(path)

    if part == "S1":
        order = ["Front Logo", "Color", "Data logo", "Inverter logo", "Power logo"]
    else:
        order = ["Eva cover", "Drawer printing", "Color logo", "Fan cover", "Shelve color"]

    codes = "".join(_get_code(data.get(k, "")) for k in order if _get_code(data.get(k, "")) != "")
    e = {"mtime": mtime, "data": data, "codes": codes, "path": path}
    CSV_CACHE[key] = e
    return e

@CreateProgram.post("/open_program")
def open_program():
    """زرار الـ CSV في الـ home — بيفتح الملف علطول من مجلد Programs"""
    payload = request.get_json(silent=True) or {}
    try:
        path = hlb.open_program_file(payload.get("name"))
        return jsonify({"ok": True, "path": path})
    except FileNotFoundError as e:
        return jsonify({"ok": False, "msg": str(e)}), 404
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@CreateProgram.get("/programs/<path:filename>")
def download_program(filename):
    return send_from_directory(PROGRAMS_DIR, filename, as_attachment=True)


# ----------------------------------------------------------------------
# راوتس كانت ناقصة: static/main.js بيناديهم وكانوا بيرجعوا 404
# ----------------------------------------------------------------------
@CreateProgram.route("/reset_error", methods=["POST"])
def reset_error():
    """resetErrorCondition() في main.js"""
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
        return jsonify({"ok": True, "msg": "Error condition reset"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@CreateProgram.route("/delete_test", methods=["POST"])
def delete_test():
    """deleteTest(name) في main.js — حذف اختبار واحد من tests.json"""
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    if not name:
        return jsonify({"ok": False, "msg": "No test name provided"}), 400

    try:
        tests = load_tests()
        remaining = [t for t in tests if t.get("name") != name]

        if len(remaining) == len(tests):
            return jsonify({"ok": False, "msg": f"Test '{name}' not found"}), 404

        save_tests(remaining)
        print(f"Test deleted: {name}")
        return jsonify({"ok": True, "msg": f"Test '{name}' deleted", "count": len(remaining)})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@CreateProgram.route("/blocked")
def blocked():
    """main.js بيعمل redirect هنا لو المستخدم فتح الـ DevTools"""
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Blocked</title></head>"
        "<body style=\"font-family:system-ui;display:flex;align-items:center;"
        "justify-content:center;height:100vh;margin:0;background:#0e1628;color:#e2e8f0\">"
        "<div style='text-align:center'><h1 style='font-size:3rem;margin:0'>&#9888;</h1>"
        "<h2>Access blocked</h2><p style='opacity:.7'>Developer tools are not allowed "
        "in this application.</p><a href='/home' style='color:#0382b8'>Back to dashboard</a>"
        "</div></body></html>",
        403,
    )


@CreateProgram.route("/reset_tests", methods=["POST"])
def reset_tests():
    """resetDefaults() في main.js — مسح كل الاختبارات الديناميكية"""
    try:
        save_tests([])
        print("All dynamic tests cleared")
        return jsonify({"ok": True, "msg": "All tests cleared"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

@CreateProgram.route("/create_program", methods=["GET", "POST"])
def page_create_program():
    tests = load_tests()
    if request.method == "POST":
        sku = request.form.get("sku", "").strip()
    
        # S1 fields to S1.csv
        ModelName = request.form.get("ModelName", "").strip()
        front_logo = request.form.get("front_logo", "").strip()
        display_logo = request.form.get("display_logo", "").strip()
        color = request.form.get("color", "").strip()
        data_logo = request.form.get("data_logo", "").strip()
        inverter_logo = request.form.get("inverter_logo", "").strip()
        power_logo = request.form.get("power_logo", "").strip()

        # S2 fields to S2.csv
        eva_cover = request.form.get("eva_cover", "").strip()
        drawer_printing = request.form.get("drawer_printing", "").strip()
        color_logo = request.form.get("color_logo", "").strip()
        fan_cover = request.form.get("fan_cover", "").strip()
        shelve_color = request.form.get("shelve_color", "").strip()

        # الاختبارات مبقتش إجبارية — الافتراضي None|00 وبيتكتب في الـ CSV
        # زي أي اختيار تاني. (نفس السلوك في fastapi_app/routers/create_program_router.py)
        DEFAULT_OPTION = "None|00"
        front_logo = front_logo or DEFAULT_OPTION
        display_logo = display_logo or DEFAULT_OPTION
        color = color or DEFAULT_OPTION
        data_logo = data_logo or DEFAULT_OPTION
        inverter_logo = inverter_logo or DEFAULT_OPTION
        power_logo = power_logo or DEFAULT_OPTION
        eva_cover = eva_cover or DEFAULT_OPTION
        drawer_printing = drawer_printing or DEFAULT_OPTION
        color_logo = color_logo or DEFAULT_OPTION
        fan_cover = fan_cover or DEFAULT_OPTION
        shelve_color = shelve_color or DEFAULT_OPTION

        errors = []
        if not sku:
            errors.append("SKU is required.")
        if not ModelName:
            errors.append("Model Name is required.")

        if errors:
            return render_template(
                "CREATE_PROGRAM_HTML.html", errors=errors, submitted=False, sku=sku,
                ModelName=ModelName, front_logo=front_logo, display_logo=display_logo,
                color=color, data_logo=data_logo, inverter_logo=inverter_logo,
                power_logo=power_logo, eva_cover=eva_cover, drawer_printing=drawer_printing,
                color_logo=color_logo, fan_cover=fan_cover, shelve_color=shelve_color,
                tests=tests
            )

        safe_sku = re.sub(r'[^\w\-]', '', sku)
        filename_s1 = f"{safe_sku}S1.csv"
        filename_s2 = f"{safe_sku}S2.csv"
        path_s1 = os.path.join(PROGRAMS_DIR, filename_s1)
        path_s2 = os.path.join(PROGRAMS_DIR, filename_s2)

        try:
            _save_csv_file(path_s1, [
                ("Model Name", ModelName),
                ("Front Logo", front_logo),
                ("Display logo", display_logo),
                ("Color", color),
                ("Data logo", data_logo),
                ("Inverter logo", inverter_logo),
                ("Power logo", power_logo),
            ])
            save_success_s1 = f"S1 saved: {filename_s1}"
            #tcp_server._log_add("INFO", f"Saved {filename_s1}")
        except Exception as e:
            save_success_s1 = None
            #tcp_server._log_add("ERROR", f"Failed saving {filename_s1}: {e}")

        try:
            _save_csv_file(path_s2, [
                ("Model Name", ModelName),
                ("Eva cover", eva_cover),
                ("Drawer printing", drawer_printing),
                ("Color logo", color_logo),
                ("Fan cover", fan_cover),
                ("Shelve color", shelve_color),
            ])
            save_success_s2 = f"S2 saved: {filename_s2}"
            #tcp_server._log_add("INFO", f"Saved {filename_s2}")
        except Exception as e:
            save_success_s2 = None
            #tcp_server._log_add("ERROR", f"Failed saving {filename_s2}: {e}")

        # ===============================
        # handle all dynamic tests (fixed + new)
        # ===============================
        for test in tests:
            station = test.get("station", "").upper()
            test_name = test.get("name", "")
            field_key = test_name.replace(" ", "_")
            selected_value = request.form.get(field_key) or DEFAULT_OPTION

            parts = selected_value.split("|", 1)
            if len(parts) == 2:
                opt_name, opt_code = parts
            else:
                opt_name, opt_code = parts[0], ""
            target_path = path_s1 if station == "S1" else path_s2
            row = (test_name, f"{opt_name}|{opt_code}" if opt_code else opt_name)

            try:
                _save_csv_file(target_path, [row], append=True)
            except Exception as e:
                print(f"Failed saving dynamic test '{test_name}' to {target_path}: {e}")
       # ===============================
        #CSV_CACHE.pop((sku, "S1"), None)
       # CSV_CACHE.pop((sku, "S2"), None)

        return render_template(
            "CREATE_PROGRAM_HTML.html",
            submitted=True,
            sku=sku,
            ModelName=ModelName,
            front_logo=front_logo, display_logo=display_logo, color=color,
            data_logo=data_logo, inverter_logo=inverter_logo, power_logo=power_logo,
            eva_cover=eva_cover, drawer_printing=drawer_printing,
            color_logo=color_logo, fan_cover=fan_cover, shelve_color=shelve_color,
            save_success_s1=save_success_s1, save_success_s2=save_success_s2,
            filename_s1=filename_s1, filename_s2=filename_s2, tests=tests
        )

    return render_template("CREATE_PROGRAM_HTML.html", submitted=False, errors=None, tests=tests)