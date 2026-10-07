from flask import Blueprint, app, request, jsonify
import json
import os

# 1. تعريف البلو برينت بدل Flask app
time_settings_bp = Blueprint('time_settings', __name__)

SETTINGS_FILE = 'time_settings.json'

DEFAULT_SETTINGS = {
    "deviceConnectTimeout": 5.0,
    "deviceRecvTimeout": 1.0,
    "clientSocketTimeout": 1.0,
    "reconnectBaseDelay": 0.5,
    "maxBackoff": 30,
    "reconnectCheckInterval": 1,
    "defaultCharDelay": 100,
    "s1CharDelay": 100,
    "s2CharDelay": 100,
    "frameDelay": 1,
    "followupDelay": 30,
    "statusRefresh": 1500,
    "logPolling": 800,
    "server4Refresh": 2000,
    "sendTimeout": 25,
    "autoSendGap": 120,
    "dbTimeout": 10,
    "ImageTimeout": 10,
    "PlcSignal": 0.1,
    "duplicateScanWindow": 120
}

@time_settings_bp.route('/time_settings', methods=['GET'])
def get_time_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            return jsonify({"ok": True, "settings": settings})
        else:
            return jsonify({"ok": True, "settings": DEFAULT_SETTINGS})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

@time_settings_bp.route('/time_settings', methods=['POST'])
def save_time_settings():
    try:
        data = request.get_json()
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})