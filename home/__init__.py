from flask import Blueprint , jsonify
from flask import render_template, request, redirect, url_for, session
import  os
import helpers as hlb
import ClientsClass as cc
import queue 

home = Blueprint(
    "home",
    __name__,
    static_folder="static",
    template_folder="templates"
)


@home.route('/home/add_to_queue', methods=['POST'])
def add_to_queue():
    data = request.json
    dummy_number = data.get('dummy_number')
    
    if not dummy_number:
        return jsonify({"status": "error", "message": "No data"}), 400

    try:
        # إضافة الرقم للكيو (block=False عشان ميعلقش الـ Request لو الكيو مليان)
        cc.queue_manual_FOR_FAILURE.put(dummy_number)
        cc.queue_manual_FOR_Proessing.put(dummy_number)
        
        print(f"New Item Added: {dummy_number}")
        print(f"Total in Queue: {cc.queue_manual_FOR_FAILURE.qsize()}")
        
        return jsonify({
            "status": "success", 
            "current_count": cc.queue_manual_FOR_FAILURE.qsize()
        }), 200
    except queue.Full:
        return jsonify({"status": "error", "message": "Queue is full!"}), 500
    
@home.route('/home/add_to_queue2', methods=['POST'])
def add_to_queue2():
    data = request.json
    dummy_number = data.get('dummy_number')
    
    if not dummy_number:
        return jsonify({"status": "error", "message": "No data"}), 400

    try:
        # إضافة الرقم للكيو (block=False عشان ميعلقش الـ Request لو الكيو مليان)
        cc.queue_manual2_FOR_FAILURE.put(value=dummy_number, block=False)
        cc.queue_manual2_FOR_Proessing.put(value=dummy_number, block=False)
        cc.is_waiting2 = False
        cc.Manual_Scanner_MODE2 = False
        
        print(f"New Item Added: {dummy_number}")
        print(f"Total in Queue: {cc.queue_manual2_FOR_FAILURE.qsize()}")
        
        return jsonify({
            "status": "success", 
            "current_count": cc.queue_manual2_FOR_FAILURE.qsize()
        }), 200
    except queue.Full:
        return jsonify({"status": "error", "message": "Queue is full!"}), 500
@home.get("/home")
def page_index():
    csv_files = []
    for file in os.listdir(hlb.CSV_SOURCE_DIR):
        if file.endswith(".csv"):
            file_path = os.path.join(hlb.CSV_SOURCE_DIR, file)
            if os.path.isfile(file_path):
                csv_files.append({
                    "name": file,
                    "path": f"/programs/{file}",
                    "size": os.path.getsize(file_path)
                })

    csv_files.sort(
        key=lambda x: os.path.getmtime(os.path.join(hlb.CSV_SOURCE_DIR, x["name"])),
        reverse=True
    )
    
    username = session.get('username', None)
    auth = session.get('auth', None)
    return render_template(
        "INDEX_HTML.html",
        username=username,
        auth=auth,
        csv_files=csv_files,
       # default_device_ip=IO_MODULE_IP,
       # default_device_port=IO_MODULE_PORT

    )