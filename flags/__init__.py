from flask import Blueprint, request, jsonify
import json
import os
import ClientsClass as cc

# 1. تعريف البلو برينت بدل Flask app
flags= Blueprint('flags', __name__)

@flags.route('/station_logs/<int:station>')
def station_logs_view(station):
    """مربّع الـ logs اللي تحت كل كارت محطة في الـ Home"""
    import station_logs
    after = request.args.get('after', 0, type=int)
    return jsonify(station_logs.since(station, after))

@flags.route('/station1_status')
def station1_status():
    return jsonify({
        "arrived": cc.your_s1_arrived_flag,   # True / False
        "result": cc.your_s1_result,           # 'pass' / 'fail' / None
        "failed_tests": getattr(cc, "your_s1_failed_tests", None),
        "dummy_number": cc.your_s1_dummy,      # string أو None
        "sku_number": cc.your_s1_sku           # string أو None
    })

@flags.route('/station2_status')
def station2_status():
    return jsonify({
        "arrived": cc.your_s2_arrived_flag,
        "result": cc.your_s2_result,
        "failed_tests": getattr(cc, "your_s2_failed_tests", None),
        "dummy_number": cc.your_s2_dummy,
        "sku_number": cc.your_s2_sku
    })