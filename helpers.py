import csv
import os,re,json
import shutil
from typing import List,Tuple,Dict,Any
import threading
import pandas as pd
import ClientsClass
import shutil
from pathlib import Path



#Globals
CSV_CACHE: Dict[Tuple[str, str], Dict] = {}
CSV_CACHE_MAX = 256
conn_str_db1_global = None
conn_str_db2_global = None
TIME_SETTINGS = {
    'deviceConnectTimeout': 5.0,
    'deviceRecvTimeout': 1.0,
    'clientSocketTimeout': 1.0,
    'reconnectBaseDelay': 0.5,
    'maxBackoff': 30,
    'reconnectCheckInterval': 1,
    'defaultCharDelay': 100,
    's1CharDelay': 100,
    's2CharDelay': 100,
    'frameDelay': 1,
    'followupDelay': 30,
    'statusRefresh': 1500,
    'logPolling': 800,
    'server4Refresh': 2000,
    'sendTimeout': 25,
    'autoSendGap': 120,
    'dbTimeout': 10,
    'ImageTimeout':10, 
    'PlcSignal' : 0.1,
    # نفس الدامي لو اتسكان تاني خلال المدة دي (ثواني) بيتخطّى — سلك عدّى قدام السكانر مثلًا
    'duplicateScanWindow': 120,
    
}
STATION1_FILE ="Station1.csv"
STATION2_FILE ="Station2.csv"
STATION2_dummies_FILE ="Station2_dummies.csv"





last_dummy_number = None
last_dummy_number2 = None
last_product_number = None
last_product_number2 = None
last_received_data = "No data received yet"

# SQL Connection specific variables
last_raw_data = "No data received yet"
last_raw_data2 = "No data received yet"
last_dummy_extracted = "No dummy extracted yet"
last_dummy_extracted2 = "No dummy extracted yet"
last_db_status = "No database operation yet"
last_db_status2 = "No database operation yet"
first_10_digits ="NO DUMMY EXTRACTED YET"
#FOR checing the new image 
image_SN1 = None
last_image_SN1 = None
image_SN2 = None
last_image_SN2 = None

# Add image counters to detect changes
image_counter_SN1 = 0
image_counter_SN2 = 0

#station2 failure indication
Station2_failure = False
#Errors Flags 
NO_CSV_ERROR = False
Manual_Scanner_MODE =False








#-----------------save images in new floder---------------


def copy_and_rename(source_file, dest_folder, new_name):
    """
    بتنقل صورة لفولدر تاني وتغير اسمها.

    source_file : مسار الصورة الأصلية
    dest_folder : الفولدر الجديد
    new_name    : الاسم الجديد (مع الامتداد)
    """
    source_file = Path(source_file)
    dest_folder = Path(dest_folder)

    if not source_file.exists():
        print("الصورة مش موجودة!")
        return None

    dest_folder.mkdir(parents=True, exist_ok=True)
    dest_file = dest_folder / new_name

    if dest_file.exists():
        print("في ملف بنفس الاسم موجود بالفعل في الفولدر الجديد!")
        return None

    shutil.copy2(str(source_file), str(dest_file))
    print(f"تم نسخ الصورة إلى: {dest_file}")
    return dest_file








#-----------------Time settings file---------------
TIME_SETTINGS_FILE = "time_settings.json"
def get_time_setting(key: str):
    try:
        with open("time_settings.json", "r", encoding="utf-8") as f:
            current_settings = json.load(f)
        value = current_settings.get(key)
        # ملف قديم مفيهوش المفتاح ده (زي duplicateScanWindow) — نرجع للافتراضي بدل None
        return TIME_SETTINGS.get(key) if value is None else value
    except Exception:
        return TIME_SETTINGS.get(key) # لو حصل مشكلة في فتح الملف يرجع القيمة الافتراضية
        
# ----------------------------------------------------------------------
# BASE_DIR لازم يبقى جنب الـ exe مش جوه الحزمة.
#
# CSV_SOURCE_DIR تحت بيتبني منه، و ClientsClass بيقرا منه ملفات
# البرامج (CreateProgram\*.csv) — ودي بيانات بيعدّلها المستخدم.
# في وضع onefile، __file__ بيشاور على فولدر مؤقت بيتفك فيه البرنامج،
# فلو سبناه كده كنا هنقرا نسخة قديمة متجمدة وقت البناء بدل النسخة
# الحقيقية اللي جنب الـ exe.
#
# __compiled__.containing_dir بيدي المكان الصح في standalone و onefile،
# ومش موجود وقت التشغيل من السورس فالـ NameError متوقع.
# ----------------------------------------------------------------------
try:
    BASE_DIR = os.path.normpath(__compiled__.containing_dir)  # type: ignore[name-defined]  # noqa: F821
except NameError:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROGRAMS_DIR = BASE_DIR

# ----------------------------------------------------------------------
# مجلد البرامج
#
# الاسم كان "CreateProgram" — نفس اسم حزمة البايثون بالظبط، وده كان
# مربك: المستخدم بيفتح الفولدر اللي جنب الـ exe وميعرفش هو ده كود ولا
# داتا. بقى اسمه "Programs" — أوضح وأنضف.
#
# LEGACY_CSV_DIR هو الاسم القديم. أي جهاز شغال دلوقتي عنده ملفات جواه،
# فبننقلها مرة واحدة أول تشغيل بعد التحديث.
# ----------------------------------------------------------------------
CSV_DIR_NAME = "Programs"
CSV_SOURCE_DIR = os.path.join(PROGRAMS_DIR, CSV_DIR_NAME)
LEGACY_CSV_DIR = os.path.join(PROGRAMS_DIR, "CreateProgram")

# المجلد مش بيتنسخ مع الـ exe — بنعمله أول تشغيل. من غيره صفحة
# Create Program مش بتقدر تكتب أي CSV في نسخة الـ exe.
try:
    os.makedirs(CSV_SOURCE_DIR, exist_ok=True)
except OSError as _exc:
    print(f"[helpers] تعذّر إنشاء مجلد البرامج {CSV_SOURCE_DIR}: {_exc}", flush=True)



def open_program_file(filename: str) -> str:
    """
    فتح ملف CSV من مجلد Programs (اللي جنب الـ exe / جنب الكود) بالبرنامج
    الافتراضي على الجهاز (Excel مثلًا).

    بناخد basename بس عشان محدش يقدر يخرج برّه مجلد Programs.
    بترجع المسار الكامل اللي اتفتح، أو بترمي FileNotFoundError.
    """
    safe_name = os.path.basename(str(filename or "").strip())
    if not safe_name.lower().endswith(".csv"):
        raise FileNotFoundError("Not a CSV file")
    path = os.path.join(CSV_SOURCE_DIR, safe_name)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{safe_name} not found in {CSV_SOURCE_DIR}")
    os.startfile(path)  # type: ignore[attr-defined]  # Windows بس
    return path

def _migrate_legacy_programs():
    """
    نقل ملفات الـ CSV من CreateProgram\\ القديم إلى Programs\\.

    بننقل ملفات .csv بس، ومش بنمسح المجلد القديم — لأن وقت التشغيل من
    السورس المجلد القديم هو حزمة البايثون نفسها (فيها __init__.py)،
    ومسحها كان هيكسر البرنامج.

    أي ملف موجود في الجديد مبيتلمسش، فالدالة دي آمنة إنها تتنفذ كل
    تشغيل — بعد أول مرة مش بتعمل حاجة.
    """
    if os.path.normcase(LEGACY_CSV_DIR) == os.path.normcase(CSV_SOURCE_DIR):
        return
    if not os.path.isdir(LEGACY_CSV_DIR):
        return

    try:
        names = os.listdir(LEGACY_CSV_DIR)
    except OSError:
        return

    for name in names:
        if not name.lower().endswith(".csv"):
            continue

        src = os.path.join(LEGACY_CSV_DIR, name)
        dst = os.path.join(CSV_SOURCE_DIR, name)
        if not os.path.isfile(src) or os.path.exists(dst):
            continue

        try:
            shutil.move(src, dst)
        except OSError:
            # لو النقل فشل (الملف مفتوح مثلًا) بننسخه بدل ما نضيّعه
            try:
                shutil.copy2(src, dst)
            except OSError:
                pass


_migrate_legacy_programs()

TESTS_FILE = "tests.json"
#-----------------check if Statin1.csv exist---------------
if not os.path.exists(STATION1_FILE):
    with open(STATION1_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["DummyNumber", "TestName", "Result"])

#-----------------check if Statin2.csv exist---------------
if not os.path.exists(STATION2_FILE):
    with open(STATION2_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["DummyNumber", "TestName", "Result"])
#-----------------check if Statin2_dummies.csv exist---------------
if not os.path.exists(STATION2_dummies_FILE):
    with open(STATION2_dummies_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["DummyNumber" , "StationResult"])

# -------------------- LOG FUNCTION --------------------
def tcp_log_print(msg):
    print(msg, flush=True)
    
#jason file for tests
def load_tests():
    if not os.path.exists(TESTS_FILE):
        return []
    with open(TESTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tests(tests):
    with open(TESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(tests, f, ensure_ascii=False, indent=2)


# ----------------------------------------------------------------------
# خيارات وأسماء الاختبارات الثابتة (كانت في localStorage بتاع المتصفح)
#
# قبل كده كانت متحفوظة في كاش الكروم، فأي مسح للكاش أو فتح البرنامج من
# متصفح/جهاز تاني كان بيرجّع كل الأكواد والأسماء للافتراضي. دلوقتي بقت
# في ملف test_options.json جنب البرنامج، فكل الأجهزة بتشوف نفس الإعداد.
#
# شكل الملف:
#   {
#     "fixed_options": { "front_logo": [["None","00"], ["Beko","1A"]], ... },
#     "labels":        { "front_logo": "Front Logo", ... }
#   }
# ----------------------------------------------------------------------
TEST_OPTIONS_FILE = os.path.join(BASE_DIR, "test_options.json")


def load_test_options() -> Dict[str, Any]:
    """قراءة الملف. بيرجع الشكل الفاضي لو الملف مش موجود أو بايظ."""
    empty = {"fixed_options": {}, "labels": {}}
    try:
        if not os.path.exists(TEST_OPTIONS_FILE):
            return empty
        with open(TEST_OPTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return empty
        fixed = data.get("fixed_options")
        labels = data.get("labels")
        return {
            "fixed_options": fixed if isinstance(fixed, dict) else {},
            "labels": labels if isinstance(labels, dict) else {},
        }
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[helpers] تعذّرت قراءة {TEST_OPTIONS_FILE} ({exc})", flush=True)
        return empty


def save_test_options(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    دمج وحفظ. بنكتب في ملف مؤقت وبعدين os.replace عشان لو البرنامج قفل
    وسط الكتابة الملف القديم ما يبوظش.
    """
    current = load_test_options()
    payload = payload if isinstance(payload, dict) else {}

    fixed = payload.get("fixed_options")
    if isinstance(fixed, dict):
        clean = {}
        for key, options in fixed.items():
            if not isinstance(options, list):
                continue
            rows = []
            for opt in options:
                if isinstance(opt, (list, tuple)) and len(opt) >= 2:
                    rows.append([str(opt[0]), str(opt[1])])
                elif isinstance(opt, dict):
                    rows.append([str(opt.get("name", "")), str(opt.get("code", ""))])
            clean[str(key)] = rows
        current["fixed_options"].update(clean)

    labels = payload.get("labels")
    if isinstance(labels, dict):
        current["labels"].update({str(k): str(v) for k, v in labels.items()})

    tmp_path = TEST_OPTIONS_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, TEST_OPTIONS_FILE)
    return current


def reset_test_options() -> Dict[str, Any]:
    """مسح الملف كله — الواجهة بترجع للقيم الافتراضية."""
    empty = {"fixed_options": {}, "labels": {}}
    tmp_path = TEST_OPTIONS_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(empty, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, TEST_OPTIONS_FILE)
    return empty
#get the path
def _csv_path(sku: str, part: str) -> str:
    safe_sku = re.sub(r'[^\w\-]', '', sku or "")
    return os.path.join(PROGRAMS_DIR, f"{safe_sku}{part}.csv")
#save the data of sku in csv 
def _save_csv_file(path: str, rows: List[Tuple[str, str]], append: bool = False):
    """append=True يضيف في آخر الملف من غير ما يكرر صف العناوين."""
    mode = "a" if append else "w"
    need_header = True

    # نتأكد إن الفولدر موجود قبل الكتابة (نسخة الـ exe مش بيبقى فيها
    # مجلد CreateProgram، وممكن كمان حد يمسحه والبرنامج شغال).
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
    
#-------------------Insert received data in csv-----------
def insert_csv_station1(Dummy, Test, Res):
    with open("Station1.csv", mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([Dummy, Test, Res])


def insert_csv_station2(dummy, test, res):
    with open("Station2.csv", mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([dummy, test, res])


def delete_row_if_contains(file_path, target_element):
    rows_to_keep = []
    
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if not row:
                continue
            
            # لو العنصر مش موجود في أي مكان في الصف، هنحتفظ بيه
            if target_element not in row:
                rows_to_keep.append(row)

    with open(file_path, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(rows_to_keep)

def insert_csv_station2_dummies(dummy, StationRes):
    with open("Station2_dummies.csv", mode='a', newline='', encoding='utf-8') as file:
        
        

        delete_row_if_contains("Station2_dummies.csv", dummy )
        writer = csv.writer(file)
        writer.writerow([dummy, StationRes])
#-------------------Clear CSV when new dummy starts-----------
def clear_station1_csv_for_new_dummy(new_dummy):
    """
    """#Clear Station1.csv and start fresh for new dummy
    """
    global current_processing_dummy_station1
    
    # Only clear if it's a different dummy
    if current_processing_dummy_station1 != new_dummy:
        current_processing_dummy_station1 = new_dummy
        
        # Clear the file and write header
        with open(STATION1_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["DummyNumber", "TestName", "Result"])
        
        """
    pass


def clear_station2_csv_for_new_dummy(new_dummy):
    pass
    '''
    """Clear Station2.csv and start fresh for new dummy"""
    global current_processing_dummy_station2
    
    # Only clear if it's a different dummy
    if current_processing_dummy_station2 != new_dummy:
        current_processing_dummy_station2 = new_dummy
        
        # Clear the file and write header
        with open(STATION2_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["DummyNumber", "TestName", "Result"])
    '''

def _load_csv_file(path: str) -> Dict[str, str]:
    out = {}
    with open(path, "r", newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            if len(row) == 2:
                out[row[0]] = row[1]
    return out

def auto_send_codes(codes: str, filename: str, csv_data: Dict[str, str], part: str, server_instance):
    """Automatically send loaded codes to appropriate server"""
    try:
        if not codes:
            server_instance._log_add("WARNING", "No codes to send automatically")
            return False
            
        server_instance._log_add("INFO", f"Auto-sending codes: {codes}")
        
        task = {
            "message": codes,
            "target": "combined",
            "encoding": "utf-8",
            "char_delay_ms": TIME_SETTINGS['s1CharDelay'] if part == "S1" else TIME_SETTINGS['s2CharDelay'],
            "retries": 1,
            "program_part": part,
            "program_label": filename,
            "program_data": csv_data,
            "event": threading.Event(),
            "result": None
        }
        
        server_instance._send_queue.put(task)
        
        if task["event"].wait(timeout=TIME_SETTINGS['sendTimeout']):
            result = task.get("result")
            if result and result.get("ok"):
                server_instance._log_add("INFO", f"Auto-send successful: {codes}")
                return True
            else:
                error_msg = result.get("msg", "Unknown error") if result else "No result"
                server_instance._log_add("ERROR", f"Auto-send failed: {error_msg}")
                return False
        else:
            server_instance._log_add("ERROR", "Auto-send timed out")
            return False
            
    except Exception as e:
        server_instance._log_add("ERROR", f"Error in auto_send_codes: {e}")
        return False

def _get_code(val: str) -> str:
    """Extract code from 'Label|Code' format"""
    if not val:
        return ""
    parts = str(val).split("|", 1)
    return parts[1].strip() if len(parts) == 2 else ""



    """Automatically load CSV file based on ProductNumber"""
    try:
        if not product_number:
            server_instance._log_add("ERROR", "No ProductNumber provided for CSV auto-load")
            return False
            
        safe_product = re.sub(r'[^\w\-]', '', product_number or "")
        if not safe_product:
            server_instance._log_add("ERROR", f"Invalid ProductNumber: {product_number}")
            return False
            
        if part not in ["S1", "S2"]:
            server_instance._log_add("INFO", f"Auto-load only supports S1/S2, not {part}")
            return False
            
        filename = f"{safe_product}{part}.csv"
        csv_path = os.path.join(PROGRAMS_DIR, filename)
        
        server_instance._log_add("INFO", f"Looking for CSV file: {filename}")
        
        if not os.path.isfile(csv_path):
            server_instance._log_add("WARNING", f"CSV file not found: {filename}")
            return False
            
        csv_data = _load_csv_file(csv_path)
        
        if part == "S1":
            order = ["Front Logo", "Color", "Data logo", "Inverter logo", "Power logo"]
        else:
            order = ["Eva cover", "Drawer printing", "Color logo", "Fan cover", "Shelve color"]
            
        codes = "".join(_get_code(csv_data.get(k, "")) for k in order if _get_code(csv_data.get(k, "")) != "")
        
        server_instance.current_program_label = filename
        server_instance.current_program_data = csv_data
        
        server_instance._log_add("AUTO_LOAD", f"PRODUCT_NUMBER_CSV_LOADED_{part}: {filename} {codes}")
        server_instance._log_add("INFO", f"Auto-loaded program: {filename} with codes: {codes}")
        
        auto_send_codes(codes, filename, csv_data, part, server_instance)
        return codes
        
    except Exception as e:
        server_instance._log_add("ERROR", f"Error in auto_load_csv_by_product_number: {e}")
        return False
    




def _failure_mode_station2_check(target_dummy=None , Client= None):
    
    """
    Check if Station2 failed for the given dummy.
    Returns: True if failed, False otherwise
    """
    try:
        # Read the Station2 dummies CSV
        station2_dummies_data = pd.read_csv(STATION2_dummies_FILE)
        
        if station2_dummies_data.empty:
            return False
        
        # Filter for the specific dummy
        if target_dummy:
            dummy_row = station2_dummies_data[
                station2_dummies_data['DummyNumber'] == target_dummy
            ]
            
            if dummy_row.empty:
                return False
            
            # Check the result column (assuming it's 'StationResult')
            result = dummy_row.iloc[0]['StationResult']
            
            return result 
        
        return False
        
    except Exception as e:
        Client._log_add("ERROR", f"Error checking Station2 failure: {e}")
        return False
