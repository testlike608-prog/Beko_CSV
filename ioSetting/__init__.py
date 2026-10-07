"""
ioSetting
---------
إعدادات الـ I/O mapping + مسارات VisionMaster، كلها في config.json.

شكل الملف الجديد:
    {
        "io_mapping":    { "LIGHTING_S1": 8, ... },
        "vision_master": { "assembly_dir": "", "solution_path": "", ... }
    }

الملف القديم كان dictionary مسطّح فيه الـ mapping بس. load_mapping() بتكتشف
الشكل القديم وبتحوّله أوتوماتيكيًا لأول مرة، فمفيش أي إعدادات بتضيع.

مهم: مسارات VisionMaster اتحطّت في قسم منفصل عن الـ mapping عن قصد —
لأن save_mapping_to_file() بتكتب القاموس كله، والواجهة بتعمل parseInt()
لكل الحقول، فلو المسارات كانت جوه نفس القاموس كانت هتتحول لـ NaN.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict

from flask import Blueprint, request, jsonify

# 1. تعريف البلو برينت بدل Flask app (لسه مستخدم في النسخة القديمة main.py)
io_mapping_bp = Blueprint('io_mapping', __name__)

CONFIG_FILE = 'config.json'

# الإعدادات الافتراضية
default_mapping = {
    "LIGHTING_S1": 8, "LIGHTING_S2": 1, "BUZZER_S1": 2, "BUZZER_S2": 3,
    "SCANNER_S1": 4, "SCANNER_S2": 5, "TESTDONE_S1": 6, "TESTDONE_S2": 7, "FAILURE": 16,
    "READ_DI0": 0, "READ_DI1": 1, "READ_INPUTS_REG": 34
}

# ----------------------------------------------------------------------
# خصائص التشغيل (features)
#
# manual_mode:
#   True  = السلوك القديم — لو السكانر فشل بيطلع Manual Scanner popup
#           والبازر بيرن لحد ما المشغّل يدخل الكود بإيده.
#   False = مفيش popup ولا بازر — بيتسجّل alert بس إن فيه تريجر من غير
#           سكان، والسيكونس بيكمّل عادي ويستنى تلاجة جديدة.
# ----------------------------------------------------------------------
default_features = {
    "manual_mode": True,
}

default_vision_master = {
    "assembly_dir": "",     # فاضي = اكتشاف أوتوماتيكي من Program Files
    "solution_path": "",    # مسار ملف .solw / .sol
}

# ----------------------------------------------------------------------
# عناوين الأجهزة (IP / Port)
#
# دي كانت متكتوبة بإيد جوه ClientsClass.py، فأي تغيير في الشبكة كان
# محتاج تعديل في الكود وإعادة بناء الـ exe. دلوقتي بقت في config.json
# وبتتظبط من مودال الإعدادات (Developer mode بس).
#
# القيم اللي هنا هي نفس القيم القديمة بالظبط، فأي خط شغال دلوقتي
# هيفضل شغال زي ما هو من غير ما حد يعمل أي حاجة.
# ----------------------------------------------------------------------
ENDPOINT_LABELS = {
    "scanner_s1":      "Scanner S1 (outer)",
    "scanner_s2":      "Scanner S2 (inner)",
    "vision_outer":    "Vision outer (S1)",
    "vision_inner":    "Vision inner (S2)",
    "vision_outer_sn": "Vision outer S/N",
    "vision_inner_sn": "Vision inner S/N",
    "io_read":         "I/O module - read",
    "io_write":        "I/O module - write",
    "cam_cap_s1":      "Camera capture S1",
    "cam_cap_s2":      "Camera capture S2",
}

default_endpoints = {
    "scanner_s1":      {"ip": "192.168.1.16", "port": 7940},
    "scanner_s2":      {"ip": "192.168.1.17", "port": 7950},
    "vision_outer":    {"ip": "127.0.0.1",    "port": 20},
    "vision_inner":    {"ip": "127.0.0.1",    "port": 30},
    "vision_outer_sn": {"ip": "127.0.0.1",    "port": 40},
    "vision_inner_sn": {"ip": "127.0.0.1",    "port": 50},
    "io_read":         {"ip": "192.168.1.30", "port": 502},
    "io_write":        {"ip": "192.168.1.30", "port": 502},
    "cam_cap_s1":      {"ip": "127.0.0.1",    "port": 70},
    "cam_cap_s2":      {"ip": "127.0.0.1",    "port": 80},
}

io_mapping: Dict[str, Any] = {}
vision_master_config: Dict[str, Any] = {}
features: Dict[str, Any] = {}
endpoints: Dict[str, Any] = {}


# ----------------------------------------------------------------------
# تحميل / حفظ
# ----------------------------------------------------------------------
def _read_config_file() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[ioSetting] تعذّرت قراءة {CONFIG_FILE} ({exc}) — هنستخدم الافتراضي")
        return {}


def _merge_endpoints(saved: Any) -> Dict[str, Any]:
    """
    بيدمج اللي في الملف مع الافتراضي.

    أي جهاز ناقص من الملف بياخد قيمته الافتراضية، وأي قيمة بايظة
    (IP فاضي أو port مش رقم) بترجع للافتراضي كمان — عشان config.json
    معطوب ميمنعش البرنامج من الاشتغال.
    """
    saved = saved if isinstance(saved, dict) else {}
    merged: Dict[str, Any] = {}

    for key, fallback in default_endpoints.items():
        entry = saved.get(key) if isinstance(saved.get(key), dict) else {}

        ip = str(entry.get("ip") or "").strip() or fallback["ip"]
        try:
            port = int(entry.get("port"))
            if not (1 <= port <= 65535):
                raise ValueError
        except (TypeError, ValueError):
            port = fallback["port"]

        merged[key] = {"ip": ip, "port": port}

    return merged


def load_mapping():
    """تحميل الإعدادات من config.json مع دعم الشكل القديم المسطّح."""
    global io_mapping, vision_master_config, endpoints, features

    data = _read_config_file()

    if not data:
        io_mapping = default_mapping.copy()
        vision_master_config = default_vision_master.copy()
        endpoints = _merge_endpoints({})
        features = default_features.copy()
        return

    if "io_mapping" in data:
        # الشكل الجديد
        io_mapping = {**default_mapping, **(data.get("io_mapping") or {})}
        vision_master_config = {
            **default_vision_master,
            **(data.get("vision_master") or {}),
        }
        # قسم endpoints مش موجود في الملفات القديمة — _merge_endpoints
        # بترجّع الافتراضي كله في الحالة دي.
        endpoints = _merge_endpoints(data.get("endpoints"))
        features = {**default_features, **(data.get("features") or {})}
        features["manual_mode"] = bool(features.get("manual_mode", True))
    else:
        # الشكل القديم: الملف كله عبارة عن mapping
        print("[ioSetting] تحويل config.json للشكل الجديد (io_mapping / vision_master)")
        io_mapping = {**default_mapping, **data}
        vision_master_config = default_vision_master.copy()
        endpoints = _merge_endpoints({})
        features = default_features.copy()
        save_config_to_file()


def save_config_to_file():
    """كتابة الملف كله (الـ mapping + VisionMaster + عناوين الأجهزة)."""
    payload = {
        "io_mapping": io_mapping,
        "vision_master": vision_master_config,
        "endpoints": endpoints,
        "features": {**default_features, **(features or {})},
    }
    tmp_path = CONFIG_FILE + ".tmp"
    with open(tmp_path, 'w', encoding='utf-8') as file:
        json.dump(payload, file, indent=4, ensure_ascii=False)
    os.replace(tmp_path, CONFIG_FILE)


def save_mapping_to_file():
    """
    محتفظين بالاسم القديم عشان الكود الموجود (io_setting_router) ما يتكسرش.
    بقت بتكتب الملف كله مش الـ mapping بس، فمسارات VisionMaster ما بتتمسحش.
    """
    save_config_to_file()


# ----------------------------------------------------------------------
# إعدادات VisionMaster
# ----------------------------------------------------------------------
def get_vision_master_config() -> Dict[str, Any]:
    """نسخة من إعدادات VisionMaster (بيستخدمها vision_master.py)."""
    return {**default_vision_master, **vision_master_config}


def save_vision_master_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    """تحديث إعدادات VisionMaster وحفظها. بترجع الإعدادات بعد التحديث."""
    global vision_master_config

    clean: Dict[str, Any] = {}
    for key in ("assembly_dir", "solution_path"):
        if key in payload:
            clean[key] = str(payload.get(key) or "").strip()

    vision_master_config = {**get_vision_master_config(), **clean}
    save_config_to_file()
    return get_vision_master_config()


# ----------------------------------------------------------------------
# خصائص التشغيل (features)
# ----------------------------------------------------------------------
def get_features() -> Dict[str, Any]:
    """نسخة من الخصائص الحالية مدموجة مع الافتراضي."""
    merged = {**default_features, **(features or {})}
    merged["manual_mode"] = bool(merged.get("manual_mode", True))
    return merged


def is_manual_mode_enabled() -> bool:
    """
    بيقراها ClientsClass وقت التشغيل مباشرة، عشان تغيير الإعداد من
    الواجهة يبقى فوري من غير Restart.
    """
    return bool(get_features().get("manual_mode", True))


def save_features(payload: Dict[str, Any]) -> Dict[str, Any]:
    """تحديث الخصائص وحفظها في config.json."""
    global features

    payload = payload if isinstance(payload, dict) else {}
    current = get_features()

    if "manual_mode" in payload:
        value = payload.get("manual_mode")
        if isinstance(value, str):
            value = value.strip().lower() in ("1", "true", "on", "yes")
        current["manual_mode"] = bool(value)

    features = current
    save_config_to_file()
    return get_features()


# ----------------------------------------------------------------------
# عناوين الأجهزة
# ----------------------------------------------------------------------
_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _valid_host(value: str) -> bool:
    """
    IPv4 أو hostname.

    بنقبل الاتنين عن قصد — في خطوط كتير الأجهزة بتتنادى بالاسم مش
    بالـ IP، ورفض الاسم كان هيبقى تضييق من غير سبب.
    """
    value = (value or "").strip()
    if not value or len(value) > 255:
        return False

    if _IPV4_RE.match(value):
        return all(0 <= int(part) <= 255 for part in value.split("."))

    # hostname: حروف وأرقام و - و . بس
    return re.match(r"^[A-Za-z0-9]([A-Za-z0-9\-\.]*[A-Za-z0-9])?$", value) is not None


def get_endpoints() -> Dict[str, Any]:
    """نسخة من عناوين الأجهزة (بيستخدمها ClientsClass)."""
    return {key: dict(value) for key, value in _merge_endpoints(endpoints).items()}


def save_endpoints(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    تحديث عناوين الأجهزة وحفظها في config.json.

    بترمي ValueError لو أي IP أو port غلط — الراوتر بيحوّلها لـ 400
    عشان المستخدم يشوف الغلط بدل ما يتحفظ عنوان بايظ ويقع وقت Start.
    """
    global endpoints

    payload = payload if isinstance(payload, dict) else {}
    current = get_endpoints()

    for key, entry in payload.items():
        if key not in default_endpoints:
            raise ValueError(f"Unknown device '{key}'")
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid entry for '{key}'")

        label = ENDPOINT_LABELS.get(key, key)

        if "ip" in entry:
            ip = str(entry.get("ip") or "").strip()
            if not _valid_host(ip):
                raise ValueError(f"{label}: invalid IP or host '{ip}'")
            current[key]["ip"] = ip

        if "port" in entry:
            try:
                port = int(entry.get("port"))
            except (TypeError, ValueError):
                raise ValueError(f"{label}: port must be a number")
            if not (1 <= port <= 65535):
                raise ValueError(f"{label}: port must be between 1 and 65535")
            current[key]["port"] = port

    endpoints = current
    save_config_to_file()
    return get_endpoints()


def reset_endpoints() -> Dict[str, Any]:
    """رجوع لعناوين المصنع الافتراضية."""
    global endpoints
    endpoints = _merge_endpoints({})
    save_config_to_file()
    return get_endpoints()


# تحميل الإعدادات عند عمل Import للملف
load_mapping()


# ----------------------------------------------------------------------
# الدالة الشاملة لبناء الكود
# ----------------------------------------------------------------------
def generate_modbus_command(function_name, action):
    if function_name not in io_mapping:
        return "Error: Function not mapped"

    pin_number = io_mapping[function_name]
    pin_hex = f"{pin_number:04X}"

    header = "00010000000601"

    if action == "ON":
        return header + "05" + pin_hex + "FF00"
    elif action == "OFF":
        return header + "05" + pin_hex + "0000"
    elif action == "READ_DI":
        return header + "02" + pin_hex + "0001"
    elif action == "READ_REG":
        return header + "03" + pin_hex + "0001"

    return "Error: Unknown action"


# ----------------------------------------------------------------------
# 2. تغيير @app.route إلى @io_mapping_bp.route (النسخة القديمة Flask)
# ----------------------------------------------------------------------
@io_mapping_bp.route('/save_mapping', methods=['POST'])
def save_mapping():
    global io_mapping
    io_mapping.update(request.json)
    save_mapping_to_file()
    return jsonify({"status": "success"})


@io_mapping_bp.route('/command', methods=['POST'])
def execute_command():
    data = request.json
    func_name = data.get("function")
    action = data.get("action")

    hex_command = generate_modbus_command(func_name, action)
    print(f"[{action}] Command for {func_name}: {hex_command}")

    # هنا كود الإرسال للموديول
    return jsonify({"command": hex_command})


@io_mapping_bp.route('/off_all', methods=['POST'])
def off_all():
    cmd_off_all = "000100000009010F00000010020000"
    print(f"Sending OFF ALL Command: {cmd_off_all}")

    return jsonify({"command": cmd_off_all, "status": "All Off Sent"})

# (ملاحظة: شيلنا جزء app.run عشان الملف ده مجرد Blueprint مش هيشتغل لوحده)
