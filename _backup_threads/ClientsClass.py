import socket
import threading
import time
import queue
import pyodbc
import os
import db
import helpers as hlb
import station_logs
import re
from typing import Dict
import textwrap 
from queue import Empty
from flask import url_for, Flask
import ioSetting
from ioSetting import generate_modbus_command

# هتحتفظ بس بالأمر ده وتمسح الباقي
CMD_OFF_ALL = "000100000009010F00000010020000"


global di 
di = dict()
global di2 
di2 = dict()


global your_s1_arrived_flag
your_s1_arrived_flag = False
global your_s1_result
your_s1_result = None
global your_s1_dummy
your_s1_dummy = ""
global your_s1_sku
your_s1_sku = ""
# آخر نتيجة فحص للمحطة 1 بالاختبارات الفاشلة — بتفضل ظاهرة في الواجهة
# لحد ما تيجي نتيجة التلاجة اللي بعدها (مش بتتمسح بعد 3 ثواني زي result)
global your_s1_failed_tests
your_s1_failed_tests = None   # {"dummy": str, "result": "PASS"/"FAIL", "tests": [..]}


global your_s2_arrived_flag 
your_s2_arrived_flag = False
global your_s2_result
your_s2_result = None
global your_s2_dummy
your_s2_dummy = ""
global your_s2_sku
your_s2_sku = ""
global your_s2_failed_tests
your_s2_failed_tests = None



global queue_manual
global queue_manual2 
global NO_CSV_ERROR
NO_CSV_ERROR = False
global NO_CSV_ERROR2
NO_CSV_ERROR2 = False
# اسم ملف الـ CSV المفقود لكل محطة (بيظهر في الـ alert)
global NO_CSV_FILE
NO_CSV_FILE = None
global NO_CSV_FILE2
NO_CSV_FILE2 = None
# تريجر جه والسكانر فشل والـ Manual mode مقفول -> alert بس من غير popup
global SCAN_SKIPPED
SCAN_SKIPPED = False
global SCAN_SKIPPED2
SCAN_SKIPPED2 = False
global SCAN_SKIPPED_COUNT
SCAN_SKIPPED_COUNT = 0
global SCAN_SKIPPED_COUNT2
SCAN_SKIPPED_COUNT2 = 0
global Buzzer_Flag_to_OFF
global Buzzer_Flag_to_OFF2
global is_waiting
global Manual_Scanner_MODE, Manual_Scanner_MODE2
Manual_Scanner_MODE = False
Manual_Scanner_MODE2 = False
is_waiting = True
is_waiting2 = True


Buzzer_Flag_to_OFF = False
Buzzer_Flag_to_OFF2 = False
# ----------------------------------------------------------------------
# عناوين الأجهزة (IP / Port)
#
# القيم دي كانت متكتوبة بإيد هنا، فأي تغيير في الشبكة كان محتاج تعديل
# في الكود وإعادة بناء الـ exe. دلوقتي مصدرها config.json وبتتظبط من
# مودال الإعدادات (Developer mode بس).
#
# الأسماء القديمة (Ip_Scanner1 … Port_write_IO) اتسابت زي ما هي عشان
# أي كود تاني بيستخدمها ما يتكسرش — بس بقت بتتملى من ioSetting.
#
# reload_endpoints() بتتنادى مرتين: مرة هنا وقت الـ import، ومرة في
# App.__init__ — يعني أي تعديل بيتطبق أول ما تدوس Restart من الواجهة،
# من غير ما تقفل البرنامج كله.
# ----------------------------------------------------------------------
Ip_Scanner1 = Port_Scanner1 = None
Ip_Scanner2 = Port_Scanner2 = None
Ip_vision_inner = Port_vision_inner = None
Ip_vision_outer = Port_vision_outer = None
Ip_vision_inner_SN = Port_vision_inner_SN = None
Ip_vision_outer_SN = Port_vision_outer_SN = None
Ip_read_IO = Port_read_IO = None
Ip_write_IO = Port_write_IO = None
Ip_cam_cap_s1 = Port_cam_cap_s1 = None
Ip_cam_cap_s2 = Port_cam_cap_s2 = None


def reload_endpoints():
    """قراءة عناوين الأجهزة من config.json وتحديث المتغيرات اللي فوق."""
    global Ip_Scanner1, Port_Scanner1, Ip_Scanner2, Port_Scanner2
    global Ip_vision_inner, Port_vision_inner, Ip_vision_outer, Port_vision_outer
    global Ip_vision_inner_SN, Port_vision_inner_SN
    global Ip_vision_outer_SN, Port_vision_outer_SN
    global Ip_read_IO, Port_read_IO, Ip_write_IO, Port_write_IO
    global Ip_cam_cap_s1, Port_cam_cap_s1, Ip_cam_cap_s2, Port_cam_cap_s2

    ioSetting.load_mapping()      # نقرا الملف من الأول عشان نلحق أي تعديل
    eps = ioSetting.get_endpoints()

    Ip_Scanner1,        Port_Scanner1        = eps["scanner_s1"]["ip"],      eps["scanner_s1"]["port"]
    Ip_Scanner2,        Port_Scanner2        = eps["scanner_s2"]["ip"],      eps["scanner_s2"]["port"]
    Ip_vision_outer,    Port_vision_outer    = eps["vision_outer"]["ip"],    eps["vision_outer"]["port"]
    Ip_vision_inner,    Port_vision_inner    = eps["vision_inner"]["ip"],    eps["vision_inner"]["port"]
    Ip_vision_outer_SN, Port_vision_outer_SN = eps["vision_outer_sn"]["ip"], eps["vision_outer_sn"]["port"]
    Ip_vision_inner_SN, Port_vision_inner_SN = eps["vision_inner_sn"]["ip"], eps["vision_inner_sn"]["port"]
    Ip_read_IO,         Port_read_IO         = eps["io_read"]["ip"],         eps["io_read"]["port"]
    Ip_write_IO,        Port_write_IO        = eps["io_write"]["ip"],        eps["io_write"]["port"]
    Ip_cam_cap_s1,      Port_cam_cap_s1      = eps["cam_cap_s1"]["ip"],      eps["cam_cap_s1"]["port"]
    Ip_cam_cap_s2,      Port_cam_cap_s2      = eps["cam_cap_s2"]["ip"],      eps["cam_cap_s2"]["port"]

    return eps


reload_endpoints()



'''
#Write
CMD_WRITE_ALL=              "000100000009010F00000010020000"                #Turn all the outputs OFF 
CMD_COMBINED_FIRST_S1 =     "000100000009010F00000010020100"                #DO0 lighting station outer control RELAY1
CMD_COMBINED_FIRST_S2 =     "000100000009010F00000010020200"                #DO1 buzzer station inner control  RELAY2
CMD_IMMEDIATE=              "000100000009010F00000010020400"                #DO2 Buzzer station outer control RELAY3
CMD_IMMEDIATE_OK=           "000100000009010F00000010020800"                #DO3 lighting inner contrtol RELAY 4
#Write to trig the Scanner
CMD_SCANNER_S1=             "000100000009010F00000010021000"                #DO4 SCANNER STATION OUTER CONTROL 
CMD_SCANNER_S2=             "000100000009010F00000010022000"                #DO5 SCANNER STATION inner CONTROL 
#Write Test Done
CMD_TestDone_S1=            "000100000009010F00000010024000"                #DO6 test done feedback STATION OUTER CONTROL 
CMD_TestDone_S2=            "000100000009010F00000010028000"                #DO7 test done feedback STATION inner CONTROL 

CMD_Feedback_PLC=           "000100000009010F00000010020001"                #DO8 feedback CONTROL 
CMD_ACTION_S1=              "000100000009010F00000010021100"                #DO0 & DO4  0001 0001 0000 0000
CMD_ACTION_S2=              "000100000009010F00000010028800"                #DO3 & DO7  1000 1000 0000 0000
CMD_Failure_Action=         "000100000009010F00000010024001"                #testdone signal & feedback

CMD_OFF_ALL=                "000100000009010F00000010020000"                # all bins off 
'''
last_product_number=0
current_dummy_station_one=0
waiting_for_station_one_result=0
dummy_number=0
last_raw_data1=0
last_dummy_number=0

last_product_number2=0
current_dummy_station_two=0
waiting_for_station_two_result=0
dummy_number=0
last_raw_data2=0
last_dummy_number2=0

image_SN1=0
image_SN2= 0

received_tests_station1 = set()
received_tests_station2 = set()
'''
test_results_dict = {}
zero_values_list  = []
'''
# Thread-safe lock for database operations
db_lock = threading.Lock()


queue_manual_FOR_FAILURE  = queue.Queue()
queue_manual_FOR_Proessing  = queue.Queue()
queue_manual2_FOR_FAILURE  = queue.Queue()
queue_manual2_FOR_Proessing = queue.Queue()
#functions 
# ---------------- Auto-load CSV by ProductNumber ----------------
def auto_load_csv_by_product_number(product_number: str, part: str, server_instance , queue: queue): # type: ignore # server_instance = client intense
    """Automatically load CSV file based on ProductNumber"""
    global NO_CSV_ERROR, NO_CSV_ERROR2,Buzzer_Flag_to_OFF, Buzzer_Flag_to_OFF2
    global NO_CSV_FILE, NO_CSV_FILE2
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
        # مصدر واحد للمسار — الفولدر اتغير اسمه من CreateProgram\ إلى
        # Programs\ وده بيتبعه أوتوماتيك.
        csv_path  = os.path.join(hlb.CSV_SOURCE_DIR, filename)
       

        
        server_instance._log_add("INFO", f"Looking for CSV file: {filename}")
        
        while not os.path.isfile(csv_path):
            server_instance._log_add("WARNING", f"CSV file not found: {filename}")
            if part == "S1":
                NO_CSV_ERROR = True
                NO_CSV_FILE = filename
            elif part == "S2":
                NO_CSV_ERROR2 = True
                NO_CSV_FILE2 = filename

            server = TCPClient(Ip_write_IO, Port_write_IO)
            if part == "S1":
                server.send_request(generate_modbus_command("BUZZER_S1", "ON"), is_hex=True)
            if part == "S2":
               server.send_request(generate_modbus_command("BUZZER_S2", "ON"), is_hex=True)
               
            while True:
                if Buzzer_Flag_to_OFF:
                    server.send_request(generate_modbus_command("BUZZER_S1", "OFF"), is_hex=True)
                    break
                
                if Buzzer_Flag_to_OFF2:
                    server.send_request(generate_modbus_command("BUZZER_S2", "OFF"), is_hex=True)
                    break
            
            time.sleep(60)  # انتظر 60 ثانية قبل إعادة التحقق من وجود الملف

        # الملف اتلاقى -> نظّف اسم الملف المفقود
        if part == "S1":
            NO_CSV_FILE = None
        elif part == "S2":
            NO_CSV_FILE2 = None

        csv_data = hlb._load_csv_file(csv_path)
        
        # 1. الحصول على جميع العناوين (الأعمدة) من ملف الـ CSV
        # نفترض أن csv_data عبارة عن قاموس (Dictionary) يمثل الصف
        all_columns = list(csv_data.keys())
        
        # 2. تحديد الكلمة التي تريد البحث عنها لنقلها للآخر
        target_word = "Front Logo" # يمكنك تغييرها لما يناسبك أو جعلها متغيرًا
        target_word2 = "Shelve color"
        
       
        
            
        # 4&3. تجميع الكود بناءً على الترتيب الجديد
       
        if part == "S1":
            order = [col for col in all_columns if col != target_word]
        
            if target_word in all_columns:
                order.append(target_word)
        else:
            order = [col for col in all_columns if col != target_word2]
        
            if target_word2 in all_columns:
                order.append(target_word2)
            
        codes = "".join(_get_code(csv_data.get(k, "")) for k in order if _get_code(csv_data.get(k, "")) != "")
        
        server_instance.current_program_label = filename
        server_instance.current_program_data = csv_data
        
        server_instance._log_add("AUTO_LOAD", f"PRODUCT_NUMBER_CSV_LOADED_{part}: {filename} {codes}")
        server_instance._log_add("INFO", f"Auto-loaded program: {filename} with codes: {codes}")
        #codes= textwrap.wrap(codes, width=2)
        queue.put(codes)
        auto_send_codes(codes, filename, csv_data, part, server_instance)
        return codes
    except Exception as e:
        server_instance._log_add("ERROR", f"Error in auto_load_csv_by_product_number: {e}")
    

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

def auto_send_codes(codes: list, filename: str, csv_data: Dict[str, str], part: str, server_instance):
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
            "char_delay_ms": hlb.get_time_setting('s1CharDelay') if part == "S1" else hlb.get_time_setting('s2CharDelay'),
            "retries": 1,
            "program_part": part,
            "program_label": filename,
            "program_data": csv_data,
            "event": threading.Event(),
            "result": None
        }
        
        #server_instance.send_request(task["message"])
        
        if task["event"].wait(timeout=hlb.get_time_setting('sendTimeout')):
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


'''
def clients_forward():
                try:
                    if is_from_csv:
                        self._log_add("INFO", f"CSV delay: 500ms")
                        time.sleep(0.5)
                    
                    if encoding == "hex":
                        blob = parse_hex(message)
                        results["clients"] = self.send_to_all(blob)
                        client_outcome["ok"] = any(v.get("ok") for v in results["clients"].values())
                        save_to_result_files(program_label, f"HEX_SENT: {message}", program_data)
                    else:
                        with self._clients_lock:
                            ids = list(self.clients.keys())
                        per_client_results = {cid: [] for cid in ids}
                        for i in range(0, len(message), 2):
                            pair = message[i:i + 2]
                            data = pair.encode("utf-8", errors="ignore")
                            for cid in ids:
                                ok, msg = self.send_to_client(cid, data)
                                per_client_results[cid].append({"ok": ok, "msg": msg, "chunk": pair})
                            time.sleep(delay / 1000.0)
                        results["clients"] = per_client_results
                        client_outcome["ok"] = any(any(item["ok"] for item in arr) for arr in per_client_results.values())
                        save_to_result_files(program_label, f"TEXT_SENT: {message}", program_data)
                except Exception as e:
                    client_outcome["ok"] = False
                    self._log_add("ERROR", f"Client forward error: {e}")

'''


















# General Class
class  TCPClient():
    def __init__(self, ip, port, timeout=None, buffer_size=4096):
        """
        :param timeout: لو خليته None هيفضل مستني للأبد لحد ما السيرفر يرد
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.buffer_size = buffer_size
        self.sock = None  # هنا هنحتفظ بالسوكيت عشان يفضل مفتوح
        self.connected = False
        # يتفعّل عند الضغط على Stop لإيقاف كل اللوبات الخلفية بشكل نظيف
        self._stop_event = threading.Event()
        self._send_queue: "queue.Queue[dict]" = queue.Queue()
        self._log_lock = threading.Lock()
        self._log_seq = 0
        self._log = list()
        self.name =""
        # المحطة اللي اللوج بتاعه يظهر تحت كارتها في الـ Home (0 = التيرمنال بس)
        self.station = 0
        self.current_program_label =""
        self.current_program_data=""

        self.shared_queue = queue.Queue()
        self.shared_queue2= queue.Queue() #FOR DUMMY shared between scanner and data proccesing function 
        self.shared_queue3= queue.Queue() # for dummies shared between scanner and i/o writer function

    # ------------------------------------------------------------------
    # Stop / restart support (used by the Start & Stop buttons in the UI)
    # ------------------------------------------------------------------
    def is_stopping(self) -> bool:
        return self._stop_event.is_set()

    def reset_stop_flag(self):
        """يُستدعى قبل Start عشان اللوبات تشتغل من جديد"""
        self._stop_event.clear()

    def stop(self):
        """إيقاف كل اللوبات الخلفية وقفل السوكيت"""
        self._stop_event.set()
        self.connected = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None

    def connect(self):
        """دالة لفتح الاتصال مرة واحدة"""
        if self._stop_event.is_set():
            return False
        try:
            if self.connected:
                    return True
            
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout) # تحديد وقت الانتظار (أو None للانتظار الدائم)
            self.sock.connect((self.ip, self.port))
            self.connected = True
            print(f"[{self.ip}] : [{self.port}] Connected successfully.")
            return True
        except Exception as e:
            print(f"[{self.ip}] : [{self.port}] Connection Failed: {e}")
            self.connected = False
            return False
            
    def ensure_connected(self):
        """تتأكد إننا متصلين، ولو مش متصلين تحاول للأبد (إلا لو اتعمل Stop)"""
        while not self.connected and not self._stop_event.is_set():
            self._log_add("INFO", f"Trying to reconnect to {self.ip}...")
            if self.connect():
                self._log_add("INFO", "Reconnected successfully!")
                break
            else:
                self._log_add("WARNING", "Retrying in 5 seconds...")
                if self._stop_event.wait(5):
                    break

    def start_reconnection_watchdog(self):
        """تشغيل خيط المراقبة في الخلفية"""
        self._stop_event.clear()
        thread = threading.Thread(target=self._connection_monitor, daemon=True)
        thread.start()

    def _connection_monitor(self):
        """الدالة اللي بتراقب الاتصال كل كام ثانية"""
        while not self._stop_event.is_set():
            if not self.connected:
                # لو لقيناه فصل، نصلحه
                self.ensure_connected()
            else:
                # لو متصل، نتأكد إنه "فعلاً" لسه شغال
                try:
                    # محاولة إرسال بايت فارغ للتأكد من الـ Socket
                    # MSG_PEEK بتشوف الداتا من غير ما تسحبها، أو ابعت حرف تافه لو السيرفر بيسمح
                    self.sock.send(b'', socket.MSG_OOB) 
                except Exception:
                    self._log_add("WARNING", "Connection lost in background!")
                    self.connected = False

            if self._stop_event.wait(3):  # افحص كل 3 ثواني
                break
    
    def _get_sock(self):
         
        local_ip, local_port = self.sock.getsockname()
        return local_ip,local_port
   
    def send_request(self, message , is_hex=False):
        """
        إرسال واستقبال فقط (بدون إغلاق الاتصال)
        """
        # بعد الضغط على Stop مش بنحاول نبعت أو نعيد الاتصال
        if self._stop_event.is_set():
            return None

        if not self.connected or self.sock is None:
            print(f"[{self.ip}]:[{self.port}] Error: Not connected! Trying to connect...")
            self.ensure_connected()
            if not self.connected or self.sock is None:
                return None


        try:
            # 1. تجهيز الرسالة
            data_to_send = None
            if isinstance(message, bytes):
                data_to_send = message
            elif is_hex:
                data_to_send = bytes.fromhex(message)
            else:
                data_to_send = message.encode('utf-8')
                #data_to_send = [chunk.encode('utf-8') for chunk in message]

            # 2. الإرسال
           
            self.sock.sendall(data_to_send)

            # 3. الاستقبال (هنا هيفضل مستني لحد ما السيرفر يرد)
            # طالما timeout=None أو وقت كبير، هيفضل واقف هنا (Blocking)
            response = self.sock.recv(self.buffer_size)

            return  response

        except (socket.timeout):
            self._log_add("WARNING", f"[{self.ip}]:[{self.port}] Timeout: Server took too long to respond.")
            return None

        except (OSError, BrokenPipeError, ConnectionResetError, socket.error) as e:
            # هنا أهم تعديل: لو حصل أي خطأ في السوكيت (السيرفر قفل أو السلك اتشال)
            print(f"[{self.ip}]:[{self.port}] Connection Lost ({e}). Reconnecting...")
            
            self.connected = False
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
                self.sock = None
            
            # محاولة إعادة الاتصال فوراً
            self.ensure_connected()
            
            # اختياري: ممكن تخليها تحاول تبعت الرسالة تاني بعد ما رجع الاتصال
            # return self.send_request(message, is_hex) 
            return None

        except Exception as e:
            print(f"[{self.ip}]:[{self.port}] General Error: {e}")
            return None
    
    '''
    def _start_monitoring(self):
        """بدء خيط المراقبة"""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._stop_monitor.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_connections, daemon=True)
            self._monitor_thread.start()

    def _monitor_connections(self):
        """فانكشن المراقبة اللي بتشيك على حالة الاتصال كل فترة"""
        print(f"[{self.ip}] Connection monitor started.")
        while not self._stop_monitor.is_set():
            if self.connected and self.sock:
                try:
                    # بنبعث "بيانات فارغة" عشان نختبر لو السوكيت لسه شغال (Keep-alive check)
                    # MSG_PEEK بيشوف البيانات من غير ما يسحبها من البافر
                    self.sock.send(b"", socket.MSG_DONTWAIT)
                except (OSError, BrokenPipeError):
                    print(f"[{self.ip}] Monitor detected broken connection!")
                    self.connected = False
                    # هنا ممكن تختار تنادي self.connect() تاني لو عايز Auto-reconnect
                    break
            time.sleep(5)  # شيك كل 5 ثواني مثلاً
     
   '''
    
    def disconnect(self):
        """إغلاق الاتصال وإيقاف المونيتور"""
        self._stop_event.set()  # وقف اللوب في المونيتور
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.sock = None
        self.connected = False
        print(f"[{self.ip}] Connection Closed.")

    def _log_add(self, level: str, msg: str, station: int = None):
        """station: لو الـ client مشترك (زي الـ IO) بنحدد المحطة من الرسالة نفسها"""
        with self._log_lock:
            self._log_seq += 1
            self._log.append((self._log_seq, time.time(), level, msg))
            if len(self._log) > 5000:
                self._log = self._log[-3000:]
        st = self.station if station is None else station
        if st:
            station_logs.add(st, self.name, level, msg)
        print(f"[{self.name}][{level}] {msg}")
    
    def start_listening(self, callback=None):
        """
        دالة لبدء عملية الاستماع في Thread منفصل
        :param callback: دالة اختيارية يتم استدعاؤها فور استلام بيانات
        """
        self.receive_queue = queue.Queue() # كيو لاستقبال البيانات
        self._stop_event.clear()
        self.listen_thread = threading.Thread(target=self._listen_loop, args=(callback,), daemon=True)
        self.listen_thread.start()
        self._log_add("INFO", f"[{self.ip}] : [{self.port}] Started listening for incoming data...")
        

    def _listen_loop(self, callback):
        """الـ Loop الداخلي اللي بيفضل مستني داتا"""
        while self.connected and not self._stop_event.is_set():
            try:
                # الكود هيفضل واقف هنا لحد ما السيرفر يبعت حاجة
                data = self.sock.recv(self.buffer_size)
                
                if not data:
                    # لو السيرفر بعت داتا فاضية معناها قفل الاتصال
                    print(f"[{self.ip}] Server closed the connection.")
                    self.connected = False
                    break
                
                if callback:
                    callback(data)
                # إضافة البيانات للكيو
                #self.receive_queue.put(data)

                # اختياري: تسجيل اللوج
                # self._log_add("INFO", f"Received data: {data}")

            except socket.timeout:
                continue # لو حصل تايم أوت يرجع يحاول يستقبل تاني
            except Exception as e:
                if self.connected:
                    print(f"[{self.ip}] Listening Error: {e}")
                    self.connected = False
                break

    def get_last_received(self, block=False, timeout=None):
        """دالة لسحب آخر داتا وصلت من الكيو"""
        try:
            return self.receive_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None


##################################################################
class App():
    def __init__(self):

        # نعيد قراءة العناوين من config.json هنا عشان أي تعديل من
        # مودال الإعدادات يتطبق مع أول Restart من غير ما نقفل التطبيق.
        reload_endpoints()

        #Scanner
        self.client_scanner_station1 = TCPClient(Ip_Scanner1, Port_Scanner1 )
        self.client_scanner_station2 = TCPClient(Ip_Scanner2, Port_Scanner2 )
           
        #Vision master
        self.client_Vision_station1 = TCPClient( Ip_vision_outer, Port_vision_outer)
        self.client_Vision_station2 = TCPClient(Ip_vision_inner, Port_vision_inner )

        self.client_Vision_station1_SN = TCPClient( Ip_vision_outer_SN, Port_vision_outer_SN)
        self.client_Vision_station2_SN = TCPClient(Ip_vision_inner_SN, Port_vision_inner_SN )
        
        """Handles data from vision master systems (ports 20, 30)"""
        self.station_one_data = {"raw": "", "dummy": "", "product": "", "db_status": ""}
        self.station_two_data = {"raw": "", "dummy": "", "product": "", "db_status": ""}
        
        
        self.lock = threading.Lock()

        # آخر دامي اتقرا في كل محطة + وقته — عشان السكان المكرر (سلك عدّى
        # قدام السكانر في نص نفس التلاجة) ميدخلش الكيو مرتين
        self._scan_lock = threading.Lock()
        self._last_scan = {1: (None, 0.0), 2: (None, 0.0)}

        # timestamps for each dummy
        self.last_dummy_time_station_one = {}  # dict {dummy_number: timestamp}
        self.last_dummy_time_station_two = {}

        #I/O Moudule
        self.client_read_io = TCPClient(Ip_read_IO, Port_read_IO, timeout=2 )
        self.client_write_io = TCPClient(Ip_write_IO, Port_write_IO, timeout=2 )

        self.cam_cap_s1= TCPClient(Ip_cam_cap_s1, Port_cam_cap_s1, timeout=2 )
        self.cam_cap_s2 = TCPClient(Ip_cam_cap_s2, Port_cam_cap_s2, timeout=2 )

        # أسماء للتيرمنال + ربط كل client بمحطته عشان اللوج يظهر تحت كارتها
        # Outer = Station 1 ، Inner = Station 2 ، الـ IO تيرمنال بس
        for client, name, station in (
            (self.client_scanner_station1,   "Scanner-S1",   1),
            (self.client_Vision_station1,    "Vision-S1",    1),
            (self.client_Vision_station1_SN, "Vision-SN-S1", 1),
            (self.cam_cap_s1,                "Camera-S1",    1),
            (self.client_scanner_station2,   "Scanner-S2",   2),
            (self.client_Vision_station2,    "Vision-S2",    2),
            (self.client_Vision_station2_SN, "Vision-SN-S2", 2),
            (self.cam_cap_s2,                "Camera-S2",    2),
            (self.client_read_io,            "IO-Read",      0),
            (self.client_write_io,           "IO-Write",     0),
        ):
            client.name = name
            client.station = station

        # علم الإيقاف العام للعملية (Start / Stop من الواجهة)
        self._stop_event = threading.Event()

        #auto connnect with data base
        #self.auto_connect_db()
        #db.auto_connect_db()

        #self.test_results_dict = dict()

    # ------------------------------------------------------------------
    # Start / Stop helpers
    # ------------------------------------------------------------------
    def all_clients(self):
        """كل عملاء الـ TCP الموجودين في التطبيق"""
        return [
            self.client_scanner_station1, self.client_scanner_station2,
            self.client_Vision_station1, self.client_Vision_station2,
            self.client_Vision_station1_SN, self.client_Vision_station2_SN,
            self.client_read_io, self.client_write_io,
            self.cam_cap_s1, self.cam_cap_s2,
        ]

    def all_queues(self):
        """كل الكيوهات المستخدمة في التطبيق"""
        return [
            self.client_scanner_station1.shared_queue,
            self.client_scanner_station1.shared_queue2,
            self.client_scanner_station1.shared_queue3,
            self.client_scanner_station2.shared_queue,
            self.client_scanner_station2.shared_queue2,
            self.client_scanner_station2.shared_queue3,
            self.client_Vision_station1.shared_queue,
            self.client_Vision_station2.shared_queue,
            queue_manual_FOR_FAILURE,
            queue_manual_FOR_Proessing,
            queue_manual2_FOR_FAILURE,
            queue_manual2_FOR_Proessing,
        ]

    def is_stopping(self) -> bool:
        return self._stop_event.is_set()

    def _is_duplicate_scan(self, station: int, dummy: str) -> bool:
        """
        True لو الدامي ده هو نفس آخر دامي في المحطة واتقرا خلال
        duplicateScanWindow ثانية (من Time Settings). غير كده بيسجّله كآخر دامي.

        المدة بتتحسب من أول سكان مقبول — السكانات المكررة مش بتمدّها،
        فلو نفس التلاجة رجعت بعد المدة (rework) بتتقري عادي.
        """
        try:
            window = float(hlb.get_time_setting('duplicateScanWindow') or 120)
        except (TypeError, ValueError):
            window = 120.0
        now = time.time()
        with self._scan_lock:
            last_dummy, last_time = self._last_scan[station]
            if dummy == last_dummy and now - last_time <= window:
                return True
            self._last_scan[station] = (dummy, now)
            return False

    def _remember_scan(self, station: int, dummy: str):
        """الإدخال اليدوي مبيتمنعش، بس بيتحسب آخر دامي للمحطة."""
        with self._scan_lock:
            self._last_scan[station] = (dummy, time.time())

    def _io_log(self, station: int, level: str, msg: str):
        """لوج السيكونس بتاع محطة معيّنة — بيتكتب على client الـ IO وبيظهر تحت كارت المحطة"""
        self.client_write_io._log_add(level, msg, station=station)

    def shutdown(self):
        """
        إيقاف العملية بالكامل:
        1. رفع علم الإيقاف عشان كل اللوبات تخرج
        2. إطفاء كل المخارج على الـ I/O module
        3. قفل كل السوكيتات
        4. إيقاظ أي ثريد واقف على queue.get()
        """
        self._stop_event.set()

        # 1. علم الإيقاف على مستوى كل عميل (بيوقف الـ watchdog والـ listener)
        for client in self.all_clients():
            client._stop_event.set()

        # 2. إطفاء كل المخارج قبل قفل الاتصال
        try:
            if self.client_write_io.connected:
                self.client_write_io.sock.sendall(bytes.fromhex(CMD_OFF_ALL))
        except Exception as e:
            print(f"[shutdown] could not send OFF_ALL: {e}")

        # 3. قفل السوكيتات
        for client in self.all_clients():
            try:
                client.stop()
            except Exception as e:
                print(f"[shutdown] error stopping {client.ip}:{client.port}: {e}")

        # 4. إيقاظ أي ثريد نايم على get()
        for q in self.all_queues():
            try:
                q.put_nowait(None)
            except Exception:
                pass

        # 5. تصفير فلاجات الواجهة
        global your_s1_arrived_flag, your_s2_arrived_flag
        global your_s1_result, your_s2_result
        global Manual_Scanner_MODE, Manual_Scanner_MODE2
        global NO_CSV_ERROR, NO_CSV_ERROR2
        global NO_CSV_FILE, NO_CSV_FILE2
        global SCAN_SKIPPED, SCAN_SKIPPED2, SCAN_SKIPPED_COUNT, SCAN_SKIPPED_COUNT2
        your_s1_arrived_flag = False
        your_s2_arrived_flag = False
        your_s1_result = None
        your_s2_result = None
        global your_s1_failed_tests, your_s2_failed_tests
        your_s1_failed_tests = None
        your_s2_failed_tests = None
        Manual_Scanner_MODE = False
        Manual_Scanner_MODE2 = False
        NO_CSV_ERROR = False
        NO_CSV_ERROR2 = False
        NO_CSV_FILE = None
        NO_CSV_FILE2 = None
        SCAN_SKIPPED = False
        SCAN_SKIPPED2 = False
        SCAN_SKIPPED_COUNT = 0
        SCAN_SKIPPED_COUNT2 = 0

    def Start_connetion(self):

        # السماح للّوبات بالعمل من جديد بعد أي Stop سابق
        self._stop_event.clear()
        for client in self.all_clients():
            client.reset_stop_flag()

        # تفريغ كافة الـ Queues لضمان بداية نظيفة.
        # مهم: بنستخدم all_queues() عشان تشمل shared_queue3 كمان،
        # وإلا الـ sentinel (None) اللي بيتحط وقت الـ Stop يفضل موجود
        # ويتقري كـ dummy غلط في التشغيلة اللي بعدها.
        queues_to_clear = self.all_queues()

        for q in queues_to_clear:
            with q.mutex: # حماية العملية لضمان عدم حدوث تداخل
                q.queue.clear() # طريقة سريعة لمسح محتويات الكيو داخلياً
                q.all_tasks_done.notify_all() # إبلاغ أي Thread منتظر بأن المهام انتهت
                q.unfinished_tasks = 0
            
        # 1. قائمة بكل الكلاينتس اللي عندك
        clients = self.all_clients()
        # 2. قفل أولي لكل السوكيتات لضمان بداية نظيفة
        print("Performing initial hard-reset on all sockets...")
        for client in clients:
            try:
                if client.sock:
                    client.sock.close()
                client.connected = False
                client.sock = None
            except:
                pass

        self.client_scanner_station1.start_reconnection_watchdog()
        self.client_read_io.start_reconnection_watchdog()
        
        self.client_write_io.start_reconnection_watchdog()
        self.client_Vision_station1.start_reconnection_watchdog()
        self.client_Vision_station2.start_reconnection_watchdog()
        self.client_scanner_station2.start_reconnection_watchdog()  
        self.client_Vision_station1_SN.start_reconnection_watchdog()
        self.client_Vision_station2_SN.start_reconnection_watchdog()
        self.cam_cap_s1.start_reconnection_watchdog()
        self.cam_cap_s2.start_reconnection_watchdog()
        
        self.client_scanner_station1.start_listening(self._scanner_station_1)
        self.client_scanner_station2.start_listening(self._scanner_station_2)
        #self.client_Vision_station1_SN.start_listening(self._SN_Proccess1)
        #self.client_Vision_station2_SN.start_listening(self._SN_Proccess2)      

        self.client_write_io.send_request(CMD_OFF_ALL,is_hex=True)


    
    
    
# servers handling
    def _IO_read(self):
            global your_s1_arrived_flag, your_s2_arrived_flag
            self.client_read_io._log_add("INFO", f"start reading from io")
            last_DI0 = b"\x00"
            last_DI1 = b"\x00"

            while self.client_read_io.connected and not self._stop_event.is_set():
                try:
                    # توليد كود القراءة بناءً على إعدادات الويب
                    cmd_di0 = generate_modbus_command("READ_DI0", "READ_DI")
                    DI0_respond = self.client_read_io.send_request(message=cmd_di0, is_hex=True)
                    
                    if DI0_respond and DI0_respond[-1:] == b"\x01" and last_DI0 == b"\x00":
                        threading.Thread(target=self._IO_Writer_station_1, daemon=True).start()
                        self.client_read_io._log_add("INFO", f"found fridg in station 1", station=1)
                        your_s1_arrived_flag = True
                    last_DI0 = DI0_respond[-1:] if DI0_respond else b"\x00"
                    
                    time.sleep(0.01)

                    cmd_di1 = generate_modbus_command("READ_DI1", "READ_DI")
                    DI1_respond = self.client_read_io.send_request(message=cmd_di1, is_hex=True)
                    
                    if DI1_respond and DI1_respond[-1:] == b"\x01" and last_DI1 == b"\x00":
                        threading.Thread(target=self._IO_Writer_station_2, daemon=True).start()
                        result2 =self.cam_cap_s2.send_request("S2")
                        self.client_read_io._log_add("INFO", f"found fridg in station 2", station=2)
                        your_s2_arrived_flag = True
                    last_DI1 = DI1_respond[-1:] if DI1_respond else b"\x00"
                    
                except Exception as e:
                    self.client_read_io._log_add("INFO", f"خطأ في القراءة: {e}")
        
    def _vision_station_1(self, codes):
        """
                تستقبل نص من الـ Queue، تقسمه حرفين حرفين، وترسله إلى Vision Master 1
        """
                
        global di
        while self.client_Vision_station1.connected and not self._stop_event.is_set():
            try:
                message_from_queue = codes#self.client_scanner_station1.shared_queue.get()
                if self._stop_event.is_set():
                    break
                # 1. التأكد أن الرسالة نصية وليست فارغة
                #if not message_from_queue:
                    #self.client_Vision_station1._log_add("INFO", f"there is no message from queue")
                #else:
                message_list= textwrap.wrap(message_from_queue, width=2)
                if "00" in message_list:
                     message_list.remove("00")
                test_results_list = []
                for i in range(len(message_list)):
                        self.client_Vision_station1._log_add("INFO", f"Sending to Vision Master 1: {message_list[i]}")
                        test_results_list.append (self.client_Vision_station1.send_request(message_list[i])) 
                    

                string_test_results_list = list()
                for i in range(len(test_results_list)):
                        string_test_results_list.append(test_results_list[i].decode("utf-8", errors="ignore"))
                    #self.client_Vision_station1._log_add("INFO", f"Sending to Vision Master 1: [{ test_results_list}]")
                #self.client_scanner_station1.shared_queue.task_done()
                    
                test_results_dict = {item.split('-')[0]: item.split('-')[1] for item in string_test_results_list}   #convert list to dictinary
                    #zero_values_list = [k for k, v in my_dict.items() if v == "0"]
                    
                    #zero_values_list = [k for k, v in my_dict.items() if v == "0"]
                #di = test_results_dict
                #self.client_Vision_station1.shared_queue.put(test_results_dict)
                self.client_Vision_station1._log_add("INFO", f"Sending to Vision Master 2: [{ test_results_dict}]")
                '''
                    self.client_Vision_station1.shared_queue.put(test_results_dict)
                    
                    TEST = self.client_Vision_station1.shared_queue.get()
                    self.client_Vision_station1._log_add("INFO", f"DATA IN THE Q : [{TEST}]")
                    '''
                    
                #time.sleep(1)
                self.client_Vision_station1._log_add("INFO", f"Sending to Vision Master 2222222222222222222222: [{ test_results_dict}]")
                self.data_processing_station1(test_results_dict)
                self.client_Vision_station1._log_add("INFO", f"Sending to Vision Master 333333333333333333333333333333: [{ test_results_dict}]")  
                #thread.start()
                    #thread.join()
                   # test_results_list.clear()
                   # test_results_dict.clear()
                break
            except Exception as e:
                if hasattr(self.client_Vision_station1, '_log_add'):
                    self.client_Vision_station1._log_add("ERROR", f"Error in _vision_station_1: {e}")
                else:
                    print(f"Error in _vision_station_1: {e}")
                break


    def _vision_station_2(self, codes):
        """
        تستقبل نص من الـ Queue، تقسمه حرفين حرفين، وترسله إلى Vision Master 1
        """
        
        global di2
        while self.client_Vision_station2.connected and not self._stop_event.is_set():
            try:
                message_from_queue = codes #self.client_scanner_station2.shared_queue.get()
                if self._stop_event.is_set():
                    break
                # 1. التأكد أن الرسالة نصية وليست فارغة
                #if not message_from_queue:
                    #self.client_Vision_station2._log_add("INFO", f"there is no message from queue")
                #else:
                message_list= textwrap.wrap(message_from_queue, width=2)
                self.client_Vision_station2._log_add("INFO", f"the list [{message_list}]")
                if "00" in message_list:
                        message_list.remove("00")
                test_results_list = []
                for i in range(len(message_list)):
                        self.client_Vision_station2._log_add("INFO", f"Sending to Vision Master 2: {message_list[i]}")
                        test_results_list.append (self.client_Vision_station2.send_request(message_list[i])) 
                    

                string_test_results_list = []
                for i in range(len(test_results_list)):
                        string_test_results_list.append(test_results_list[i].decode("utf-8", errors="ignore"))
                    #self.client_Vision_station1._log_add("INFO", f"Sending to Vision Master 1: [{ test_results_list}]")
                #self.client_scanner_station2.shared_queue.task_done()
                    
                test_results_dict = {item.split('-')[0]: item.split('-')[1] for item in string_test_results_list}   #convert list to dictinary
                    #zero_values_list = [k for k, v in my_dict.items() if v == "0"]
                    
                    #zero_values_list = [k for k, v in my_dict.items() if v == "0"]
                    
                    # Use independent copies to avoid cross-thread mutation (clear/pop) side effects.
                queued_results = dict(test_results_dict)
                #self.client_Vision_station2.shared_queue.put(queued_results)
                di2 = dict(queued_results)
                self.client_Vision_station2._log_add("INFO", f"Sending to Vision Master 2: [{ test_results_dict}]")
                self.client_Vision_station2._log_add("INFO", f"Sending to Vision Master 2 DI2: [{di2}]")
                '''
                    self.client_Vision_station1.shared_queue.put(test_results_dict)
                    
                    TEST = self.client_Vision_station1.shared_queue.get()
                    self.client_Vision_station1._log_add("INFO", f"DATA IN THE Q : [{TEST}]")
                    '''
                    
                time.sleep(1)
                self.client_Vision_station2._log_add("INFO", f"before data processing2")
    
                self.data_processing_station2(test_results_dict)
                   
                #thread.start()
                    #thread.join()
                   # test_results_list.clear()
                   # test_results_dict.clear()
                break
            except Exception as e:
                if hasattr(self.client_Vision_station2, '_log_add'):
                    self.client_Vision_station2._log_add("ERROR", f"Error in _vision_station_2: {e}")
                else:
                    print(f"Error in _vision_station_2: {e}")
                break


 #finished
    def _scanner_station_1(self, data : bytes):
        """Process data from vision check 1 (port 7940)"""
        global last_product_number, current_dummy_station_one, waiting_for_station_one_result,dummy_number,last_raw_data1,last_dummy_number
        global your_s1_dummy
        try:
            text = data.decode("utf-8", errors="ignore").strip()
            if len(text) > 14:
                text = text[:14]
            
            with self.lock:
                self.station_two_data["raw"] = text
                last_raw_data2= text
            self.client_scanner_station1._log_add("INFO", f"Vision Station one data: '{text}'")
            
            if text.startswith("R"):
                parts = text.split("-")
                dummy_number = parts[0].strip()
                now2 = time.time()

                # نفس آخر دامي (سكان مكرر) — نتخطّاه قبل ما يلمس الكيو أو الـ GUI
                if self._is_duplicate_scan(1, dummy_number):
                    self.client_scanner_station1._log_add(
                        "WARNING", f"Duplicate scan skipped: {dummy_number} (same as last dummy)")
                    return

                self.client_scanner_station1.shared_queue2.put(dummy_number) # for data processing function
                self.client_scanner_station1.shared_queue3.put(dummy_number)
                your_s1_dummy = dummy_number

                
                with self.lock:
                     '''
                     last_time2 = self.last_dummy_time_station_two.get(dummy_number, 0)
                     if dummy_number == last_dummy_number2:
                        if now2 - last_time2 <= 60:
                            return
                        else:
                            tcp_server._log_add("WARNING", f"Duplicate dummy ignored: {dummy_number}")

                            return 
                   
                '''
                # CLEAR CSV FOR NEW DUMMY  ← NEW LINE
                hlb.clear_station2_csv_for_new_dummy(dummy_number)
          
                self.last_dummy_time_station_one[dummy_number] = now2
                self.station_one_data["dummy"] = dummy_number
                waiting_for_station_one_result = True
                current_dummy_station_one = dummy_number
                received_tests_station1.clear()
                last_dummy_number = dummy_number
                self.client_scanner_station1._log_add("INFO", f"Station : Extracted dummy '{dummy_number}'")
                
                #time.sleep(0.1)  # Prevent DB contention
                
        except Exception as e:
            self.client_scanner_station1._log_add("ERROR", f"Error processing Station Two data: {e}")

    def Manual_scanner_station_1(self, data : bytes):
            """Process data from vision check 1 (port 7940)"""
            global last_product_number, current_dummy_station_one, waiting_for_station_one_result,dummy_number,last_raw_data1,last_dummy_number
            global your_s1_dummy, your_s1_sku
            try:
                text = data.decode("utf-8", errors="ignore").strip()
                if len(text) > 14:
                    text = text[:14]
                
                with self.lock:
                    self.station_two_data["raw"] = text
                    last_raw_data2= text
                self.client_scanner_station1._log_add("INFO", f"Vision Station one data: '{text}'")
                
                if text.startswith("R"):
                    parts = text.split("-")
                    dummy_number = parts[0].strip()
                    now2 = time.time()

                    with self.lock:
                        '''
                        last_time2 = self.last_dummy_time_station_two.get(dummy_number, 0)
                        if dummy_number == last_dummy_number2:
                            if now2 - last_time2 <= 60:
                                return
                            else:
                                tcp_server._log_add("WARNING", f"Duplicate dummy ignored: {dummy_number}")

                                return 
                        '''
                
                    # CLEAR CSV FOR NEW DUMMY  ← NEW LINE
                    hlb.clear_station2_csv_for_new_dummy(dummy_number)
            
                    self._remember_scan(1, dummy_number)
                    self.last_dummy_time_station_one[dummy_number] = now2
                    self.station_one_data["dummy"] = dummy_number
                    waiting_for_station_one_result = True
                    current_dummy_station_one = dummy_number
                    received_tests_station1.clear()
                    last_dummy_number = dummy_number
                    self.client_scanner_station1._log_add("INFO", f"Station : Extracted dummy '{dummy_number}'")
                    return dummy_number
                    #time.sleep(0.1)  # Prevent DB contention
                  
            except Exception as e:
                self.client_scanner_station1._log_add("ERROR", f"Error processing Station Two data: {e}")

    def _scanner_station_2(self, data : bytes):
        """Process data from vision check 2 (port 7950)"""
        global last_product_number2, current_dummy_station_two, waiting_for_station_two_result,dummy_number,last_raw_data2,last_dummy_number2
        global your_s2_dummy, your_s2_sku
        try:
            text = data.decode("utf-8", errors="ignore").strip()
            if len(text) > 14:
                text = text[:14]
            
            with self.lock:
                self.station_two_data["raw"] = text
                last_raw_data2= text
            self.client_scanner_station2._log_add("INFO", f"Vision Station Two data: '{text}'")
            
            if text.startswith("R"):
                parts = text.split("-")
                dummy_number = parts[0].strip()
                now2 = time.time()

                # نفس آخر دامي (سكان مكرر) — نتخطّاه قبل ما يلمس الكيو أو الـ GUI
                if self._is_duplicate_scan(2, dummy_number):
                    self.client_scanner_station2._log_add(
                        "WARNING", f"Duplicate scan skipped: {dummy_number} (same as last dummy)")
                    return

                self.client_scanner_station2.shared_queue2.put(dummy_number)
                self.client_scanner_station2.shared_queue3.put(dummy_number)
                your_s2_dummy = dummy_number
                
                with self.lock:
                    '''
                     last_time2 = self.last_dummy_time_station_two.get(dummy_number, 0)
                     if dummy_number == last_dummy_number2:
                        if now2 - last_time2 <= 60:
                            return
                        else:
                            tcp_server._log_add("WARNING", f"Duplicate dummy ignored: {dummy_number}")

                            return 
                    '''
               
                # CLEAR CSV FOR NEW DUMMY  ← NEW LINE
                hlb.clear_station2_csv_for_new_dummy(dummy_number)
          
                self.last_dummy_time_station_two[dummy_number] = now2
                self.station_two_data["dummy"] = dummy_number
                waiting_for_station_two_result = True
                current_dummy_station_two = dummy_number
                received_tests_station2.clear()
                last_dummy_number2 = dummy_number
                self.client_scanner_station2._log_add("INFO", f"Station Two: Extracted dummy '{dummy_number}'")
                return dummy_number
                #time.sleep(0.1)  # Prevent DB contention
                
        except Exception as e:
            self.client_scanner_station2._log_add("ERROR", f"Error processing Station Two data: {e}")

    def Manual_scanner_station_2(self, data : bytes):
            """Process data from vision check 2 (port 7950)"""
            global last_product_number2, current_dummy_station_two, waiting_for_station_two_result,dummy_number,last_raw_data2,last_dummy_number2
            global your_s2_sku
            try:
                text = data.decode("utf-8", errors="ignore").strip()
                if len(text) > 14:
                    text = text[:14]
                
                with self.lock:
                    self.station_two_data["raw"] = text
                    last_raw_data2= text
                self.client_scanner_station2._log_add("INFO", f"Vision Station Two data: '{text}'")
                
                if text.startswith("R"):
                    parts = text.split("-")
                    dummy_number = parts[0].strip()
                    now2 = time.time()
                    
                    

                    with self.lock:
                        '''
                        last_time2 = self.last_dummy_time_station_two.get(dummy_number, 0)
                        if dummy_number == last_dummy_number2:
                            if now2 - last_time2 <= 60:
                                return
                            else:
                                tcp_server._log_add("WARNING", f"Duplicate dummy ignored: {dummy_number}")

                                return 
                        '''
                
                    # CLEAR CSV FOR NEW DUMMY  ← NEW LINE
                    hlb.clear_station2_csv_for_new_dummy(dummy_number)
            
                    self._remember_scan(2, dummy_number)
                    self.last_dummy_time_station_two[dummy_number] = now2
                    self.station_two_data["dummy"] = dummy_number
                    waiting_for_station_two_result = True
                    current_dummy_station_two = dummy_number
                    received_tests_station2.clear()
                    last_dummy_number2 = dummy_number
                    self.client_scanner_station2._log_add("INFO", f"Station Two: Extracted dummy '{dummy_number}'")
                    
                    #time.sleep(0.1)  # Prevent DB contention
                    
                    if db.conn_str_db1_global:
                        with db_lock:
                            try:
                                with pyodbc.connect(db.conn_str_db1_global, timeout=hlb.get_time_setting('dbTimeout')) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        "SELECT ProductNumber FROM SFCNumbers WHERE LTRIM(RTRIM(Number)) = ?",
                                        (dummy_number,)
                                    )
                                    row = cursor.fetchone()

                                if row:
                                    last_product_number2 = row[0]
                                    status = f"Found ProductNumber: {last_product_number2}"
                                    your_s2_sku = last_product_number2
                                    with self.lock:
                                        self.station_two_data["product"] = last_product_number2
                                        self.station_two_data["db_status"] = status
                                    self.client_scanner_station2._log_add("INFO", status)
                                    
                                    threading.Thread(target=auto_load_csv_by_product_number, args= (last_product_number2, "S2", self.client_Vision_station2, self.client_scanner_station2.shared_queue)).start()
                                else:
                                    status = f"Dummy '{dummy_number}' not found"
                                    with self.lock:
                                        self.station_two_data["db_status"] = status
                                    self.client_scanner_station2._log_add("WARNING", status)
                                    
                            except Exception as db_ex:
                                status = f"DB query error: {db_ex}"
                                with self.lock:
                                    self.station_two_data["db_status"] = status
                                self.client_scanner_station2._log_add("ERROR", status)
                    else:
                        with self.lock:
                            self.station_two_data["db_status"] = "No DB connection"
                            self.client_scanner_station2._log_add("WARN", "No DB connection")
            except Exception as e:
                self.client_scanner_station2._log_add("ERROR", f"Error processing Station Two data: {e}")


    def _SN_Proccess1(self,data):
        global image_SN1
    
        try:
            # التأكد من نوع البيانات: لو بايتس حولها لسترينج، لو سترينج استخدمها مباشرة
            if isinstance(data, bytes):
                text = data.decode("utf-8", errors="ignore").strip()
            else:
                text = str(data).strip()

            Chunks = text.split("-")
            
            if Chunks[0] == "SN" and len(Chunks) > 1:
                image_SN1 = Chunks[1]
                # ملحوظة: هل تقصد أن تسجيل الرقم "ERROR" أم معلومة عادية "INFO"؟
                self.client_Vision_station1_SN._log_add("ERROR", f"Image serial Number Station1 {image_SN1}")
            else:
                self.client_Vision_station1_SN._log_add("ERROR", f"UNEXPECTED INCOMING DATA: {text}")

        except Exception as e:
            self.client_Vision_station1_SN._log_add("ERROR", f"Process Error: {e}")
          

    def _SN_Proccess2(self,data):
        global image_SN2
    
        try:
            # التأكد من نوع البيانات: لو بايتس حولها لسترينج، لو سترينج استخدمها مباشرة
            if isinstance(data, bytes):
                text = data.decode("utf-8", errors="ignore").strip()
            else:
                text = str(data).strip()

            Chunks = text.split("-")
            
            if Chunks[0] == "SN" and len(Chunks) > 1:
                image_SN2 = Chunks[1]
                # ملحوظة: هل تقصد أن تسجيل الرقم "ERROR" أم معلومة عادية "INFO"؟
                self.client_Vision_station2_SN._log_add("ERROR", f"Image serial Number Station2 {image_SN2}")
            else:
                self.client_Vision_station2_SN._log_add("ERROR", f"UNEXPECTED INCOMING DATA: {text}")

        except Exception as e:
            self.client_Vision_station2_SN._log_add("ERROR", f"Process Error: {e}")
          
   
    def _IO_Writer_station_1(self):
        
       #self.client_write_io.send_request(message=CMD_ACTION_S1, is_hex=True)
        """
            Handle Station 1 device action with proper image waiting logic
            """
        self._io_log(1, "INFO", f"entered the seq of station 1")

        global Manual_Scanner_MODE, NO_CSV_ERROR, Buzzer_Flag_to_OFF,di
        global SCAN_SKIPPED, SCAN_SKIPPED_COUNT
        global image_SN1, queue_manual_FOR_FAILURE, is_waiting  # Make sure we can access these
        global your_s1_result, your_s1_dummy, your_s1_arrived_flag, your_s1_sku

        try:
            
            # ---- initial sequence ----
            self.client_write_io.send_request(generate_modbus_command("LIGHTING_S1", "ON"), is_hex=True)   # lighting ON
            #self.client_write_io.send_request(generate_modbus_command("SCANNER_S1", "ON"), is_hex=True)    # scanner ON
            result =self.cam_cap_s1.send_request("S1")
            self.client_write_io.send_request(generate_modbus_command("TESTDONE_S1", "ON"), is_hex=True)
            plc_signal_period = hlb.get_time_setting('PlcSignal')
            time.sleep(plc_signal_period)
            self.client_write_io.send_request(generate_modbus_command("TESTDONE_S1", "OFF"), is_hex=True)

            
            time.sleep(0.5)
            #self.client_write_io.send_request(generate_modbus_command("SCANNER_S1", "OFF"), is_hex=True)   # scanner OFF
            self.client_scanner_station1._log_add("info", f"light on")

            time.sleep(0.5)
            self.client_write_io.send_request(generate_modbus_command("LIGHTING_S1", "OFF"), is_hex=True)   # lighting OFF

            try:
                
                dummy= ""
                if  not self.client_scanner_station1.shared_queue3.empty():
                    
                     queue = self.client_scanner_station1.shared_queue3
                     dummy = queue.get_nowait()
                     #self.client_scanner_station1.shared_queue3.task_done()
                     
                     self.client_scanner_station1._log_add("INFO", f"I GOT THE DUMMY [{dummy}]")
                     self.client_write_io.send_request(generate_modbus_command("SCANNER_S1", "OFF"), is_hex=True)    # scanner Off
                else:
                    #queue_manual_FOR_FAILURE.queue.clear() # طريقة سريعة لمسح محتويات الكيو داخلياً
                    #queue_manual_FOR_FAILURE.all_tasks_done.notify_all() # إبلاغ أي Thread منتظر بأن المهام انتهت
                    #self.client_write_io.send_request(generate_modbus_command("SCANNER_S1", "OFF"), is_hex=True)    # scanner Off
                    
                    self.client_scanner_station1._log_add("info", f"Manual_Scanner_MODE [{Manual_Scanner_MODE}]")

                    # ---- Manual mode OFF ----
                    # مفيش popup ولا بازر: بنسجّل alert بس إن جه تريجر
                    # من غير سكان، وبنسيب السيكونس يستنى تلاجة جديدة.
                    if not ioSetting.is_manual_mode_enabled():
                        SCAN_SKIPPED = True
                        SCAN_SKIPPED_COUNT += 1
                        Manual_Scanner_MODE = False
                        self.client_scanner_station1._log_add(
                            "WARNING",
                            "S1: trigger received but scanning failed — manual mode is OFF, skipping this fridge",
                        )
                        di.clear()
                        return

                    Manual_Scanner_MODE = True
                    while  is_waiting and not self._stop_event.is_set():

                        self.client_write_io.send_request(generate_modbus_command("BUZZER_S1", "ON"), is_hex=True)  # buzzer on

                    self.client_write_io.send_request(generate_modbus_command("BUZZER_S1", "OFF"), is_hex=True)  # buzzer off
                    is_waiting = True

                    if self._stop_event.is_set():
                        return

                    self.client_scanner_station1._log_add("info", f"heyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy")

                    queue = queue_manual_FOR_FAILURE
                    dummy = queue.get()
                    if dummy is None or self._stop_event.is_set():
                        return
                    your_s1_dummy = dummy
                
                        #queue_manual_FOR_FAILURE.task_done()                  
                    self.client_write_io.send_request(generate_modbus_command("SCANNER_S1", "OFF"), is_hex=True)    # scanner Off
                    self.client_scanner_station1._log_add("info", f"{type(dummy)}")  # R0124090500055
                    text = dummy.encode("utf-8")
                    dummy = self.Manual_scanner_station_1(text)
                    self.client_scanner_station1._log_add("info", f"arrivedddddddddddddddddddddddddddddddddd")  # R0124090500055
                dummy_number = dummy
                if db.conn_str_db1_global:
                                        with db_lock:
                                            try:
                                                with pyodbc.connect(db.conn_str_db1_global, timeout=hlb.get_time_setting('dbTimeout')) as conn:
                                                    cursor = conn.cursor()
                                                    cursor.execute(
                                                        "SELECT ProductNumber FROM SFCNumbers WHERE LTRIM(RTRIM(Number)) = ?",
                                                        (dummy_number,)
                                                    )
                                                    row = cursor.fetchone()
                    
                                                if row:
                                                    last_product_number = row[0]
                                                    status = f"Found ProductNumber: {last_product_number}"
                                                    your_s1_sku = last_product_number
                                                    with self.lock:
                                                        self.station_one_data["product"] = last_product_number
                                                        self.station_one_data["db_status"] = status
                                                    self.client_scanner_station1._log_add("INFO", status)
                                                    
                                                    threading.Thread(target=self.auto_load_csv_by_product_number, args= (last_product_number, "S1", self.client_Vision_station1, self.client_scanner_station1.shared_queue)).start()
                                                else:
                                                    status = f"Dummy '{dummy_number}' not found"
                                                    with self.lock:
                                                        self.station_one_data["db_status"] = status
                                                    self.client_scanner_station1._log_add("WARNING", status)
                                                    
                                            except Exception as db_ex:
                                                status = f"DB query error: {db_ex}"
                                                with self.lock:
                                                    self.station_one_data["db_status"] = status
                                                self.client_scanner_station1._log_add("ERROR", status)
                else:
                                        with self.lock:
                                            self.station_one_data["db_status"] = "No DB connection"
                                            self.client_scanner_station1._log_add("WARN", "No DB connection")
                        
            except Exception as e:
                   self.client_scanner_station1._log_add("FATAL", f"ERROR WHILE SCANNING DUMMY NUMBER: {e}")
        except Exception as e:
            self._io_log(1, "FATAL", f"S1 device init error: {e}")
            self.client_write_io.send_request(CMD_OFF_ALL,is_hex=True)
            return

        # FIX: Capture the starting state before waiting
        start_time = time.time()
        initial_image_state = image_SN1  # Remember what image_SN1 was at the start
        image_timeout = hlb.get_time_setting('ImageTimeout')
        
        self._io_log(1, "INFO", f"Waiting for new image. Current state: {initial_image_state}")

        # ---- wait for NEW image ----
        # FIX: Proper loop with three conditions:
        # 1. Wait while we haven't received a new image
        # 2. New image means: image_SN1 changed from initial_image_state
        # 3. AND image_SN1 is not None
        image_received = False
        your_s1_arrived_flag = False
        while not image_received and not self._stop_event.is_set():
            current_time = time.time()
            #self._io_log(1, "INFO", f"entered whileeeeeeeeeeeeeeee")
            
            # Check if we got a new image
            if "FrontLogo" in di:
                self._io_log(1, "INFO", f"entered while and ifffffffff")
                #res = self.client_Vision_station1_SN.send_request("O", is_hex= False)
                self._io_log(1, "INFO", f"moveddddddddddddddddddddddddddddddd")
                self._SN_Proccess1(self.client_Vision_station1_SN.send_request("O"))
                
                if image_SN1 is not None and image_SN1 != initial_image_state:
                    self._io_log(1, "INFO", f"New image received: {image_SN1}")
                   
                    result =  hlb._failure_mode_station2_check(target_dummy=dummy, Client= self.client_scanner_station1)
                    if result == "FAIL" :
                        self.client_write_io.send_request(generate_modbus_command("FAILURE", "ON"), is_hex=True)
                        plc_signal_period = hlb.get_time_setting('PlcSignal')
                        self.client_write_io.send_request(generate_modbus_command("FAILURE", "OFF"), is_hex=True)
                    image_received = True
        try:
            queue.task_done()
        except Exception:
            pass
        di.clear()
        '''
            # Check for timeout
            if current_time - start_time > image_timeout:
                self._log_add("WARNING", f"Image timeout after {image_timeout} seconds")
                break
        '''
            # Wait a bit before checking again
        time.sleep(0.1)

        # UI: keep "Fridge Arrived" true for the whole wait loop; clear once this cycle finishes
        your_s1_arrived_flag = False

        # ---- image received successfully ----
        last_image_SN1 = image_SN1
        self._io_log(1, "INFO", f"Image processing complete for: {image_SN1}")
        
    
    
    def _IO_Writer_station_2(self):
             #self.client_write_io.send_request(message=CMD_ACTION_S1, is_hex=True)
        """
            Handle Station 1 device action with proper image waiting logic
            """
        self._io_log(2, "INFO", f"entered the seq of station 2")

        global Manual_Scanner_MODE2, NO_CSV_ERROR2, Buzzer_Flag_to_OFF2
        global SCAN_SKIPPED2, SCAN_SKIPPED_COUNT2
        global image_SN2, queue_manual2_FOR_FAILURE, is_waiting2  # Make sure we can access these
        global your_s2_arrived_flag, your_s2_dummy, your_s2_result, your_s2_sku
        queue = None
        try:
            
            # ---- initial sequence ----
            self._io_log(2, "INFO", "S2 step: LIGHTING_S2 ON")
            self.client_write_io.send_request(generate_modbus_command("LIGHTING_S2", "ON"), is_hex=True)   # lighting ON
            self._io_log(2, "INFO", "S2 step: SCANNER_S2 ON")
            self.client_write_io.send_request(generate_modbus_command("SCANNER_S2", "ON"), is_hex=True)    #  scanner ON
            self._io_log(2, "INFO", "S2 step: capture trigger S2")
            result2 =self.cam_cap_s2.send_request("S2")
            self._io_log(2, "INFO", f"S2 capture trigger response: {result2}")
            

            time.sleep(0.7)
            self.client_write_io.send_request(generate_modbus_command("SCANNER_S2", "OFF"), is_hex=True)    #  scanner OFF
            self.client_scanner_station2._log_add("info", f"light on")

            time.sleep(0.5)
            self.client_write_io.send_request(generate_modbus_command("TESTDONE_S2", "ON"), is_hex=True)

            plc_signal_period = hlb.get_time_setting('PlcSignal')
            time.sleep(plc_signal_period)
            self.client_write_io.send_request(generate_modbus_command("TESTDONE_S2", "OFF"), is_hex=True)
            self.client_write_io.send_request(generate_modbus_command("LIGHTING_S2", "OFF"), is_hex=True)   # lighting OFF
            try:
                
                dummy= ""
                if  not self.client_scanner_station2.shared_queue3.empty():
                    
                     queue = self.client_scanner_station2.shared_queue3
                     dummy = queue.get_nowait()
                     #self.client_scanner_station1.shared_queue3.task_done()
                     
                     self.client_scanner_station2._log_add("INFO", f"I GOT THE DUMMY [{dummy}]")
                     self.client_write_io.send_request(generate_modbus_command("SCANNER_S2", "OFF"), is_hex=True)    # scanner Off
                else:
                    #queue_manual_FOR_FAILURE.queue.clear() # طريقة سريعة لمسح محتويات الكيو داخلياً
                    #queue_manual_FOR_FAILURE.all_tasks_done.notify_all() # إبلاغ أي Thread منتظر بأن المهام انتهت
                    self.client_write_io.send_request(generate_modbus_command("SCANNER_S2", "OFF"), is_hex=True)    # scanner Off
                    
                    self.client_scanner_station2._log_add("info", f"Manual_Scanner_MODE2 [{Manual_Scanner_MODE2}]")

                    # ---- Manual mode OFF ----  (نفس منطق المحطة 1)
                    if not ioSetting.is_manual_mode_enabled():
                        SCAN_SKIPPED2 = True
                        SCAN_SKIPPED_COUNT2 += 1
                        Manual_Scanner_MODE2 = False
                        self.client_scanner_station2._log_add(
                            "WARNING",
                            "S2: trigger received but scanning failed — manual mode is OFF, skipping this fridge",
                        )
                        di2.clear()
                        return

                    Manual_Scanner_MODE2 = True
                    is_waiting2 = True
                    if is_waiting2:
                        self.client_write_io.send_request(generate_modbus_command("BUZZER_S2", "ON"), is_hex=True)  # buzzer on while waiting
                    while is_waiting2 and not self._stop_event.is_set():
                        time.sleep(0.5)
                    self.client_write_io.send_request(generate_modbus_command("BUZZER_S2", "OFF"), is_hex=True)  # buzzer off

                    if self._stop_event.is_set():
                        return

                    self.client_scanner_station2._log_add("info", f"heyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy")

                    queue = queue_manual2_FOR_FAILURE
                    dummy = queue.get()
                    if dummy is None or self._stop_event.is_set():
                        return
                    your_s2_dummy = dummy
                        #queue_manual_FOR_FAILURE.task_done()                 
                    self.client_write_io.send_request(generate_modbus_command("SCANNER_S2", "OFF"), is_hex=True)    # scanner Off
                    self.client_scanner_station2._log_add("info", f"{type(dummy)}")  # R0124090500055
                    text = dummy.encode("utf-8")    
                    dummy=self.Manual_scanner_station_2(text)
                   
                    is_waiting2 = True
                    #thread.join()
                    self.client_scanner_station2._log_add("info", f"arriveddddddddddddddddddddddddddddd")  # R0124090500055

                dummy_number = dummy
                if db.conn_str_db1_global:
                                         with db_lock:
                                             try:
                                                 with pyodbc.connect(db.conn_str_db1_global, timeout=hlb.get_time_setting('dbTimeout')) as conn:
                                                     cursor = conn.cursor()
                                                     cursor.execute(
                                                         "SELECT ProductNumber FROM SFCNumbers WHERE LTRIM(RTRIM(Number)) = ?",
                                                         (dummy_number,)
                                                     )
                                                     row = cursor.fetchone()
                     
                                                 if row:
                                                     last_product_number2 = row[0]
                                                     status = f"Found ProductNumber: {last_product_number2}"
                                                     your_s2_sku = last_product_number2
                                                     with self.lock:
                                                         self.station_two_data["product"] = last_product_number2
                                                         self.station_two_data["db_status"] = status
                                                     self.client_scanner_station2._log_add("INFO", status)
                                                     
                                                     threading.Thread(target=self.auto_load_csv_by_product_number, args= (last_product_number2, "S2", self.client_Vision_station2, self.client_scanner_station2.shared_queue)).start()
                                                 else:
                                                     status = f"Dummy '{dummy_number}' not found"
                                                     with self.lock:
                                                         self.station_two_data["db_status"] = status
                                                     self.client_scanner_station2._log_add("WARNING", status)
                                                     
                                             except Exception as db_ex:
                                                 status = f"DB query error: {db_ex}"
                                                 with self.lock:
                                                     self.station_two_data["db_status"] = status
                                                 self.client_scanner_station2._log_add("ERROR", status)
                else:
                                         with self.lock:
                                             self.station_two_data["db_status"] = "No DB connection"
                                             self.client_scanner_station2._log_add("WARN", "No DB connection")   
            except Exception as e:
                   self.client_scanner_station2._log_add("FATAL", f"ERROR WHILE SCANNING DUMMY NUMBER: {e}")
        except Exception as e:
            self._io_log(2, "FATAL", f"S2 device init error: {e}")
            self.client_write_io.send_request(CMD_OFF_ALL,is_hex=True)
            return

        # FIX: Capture the starting state before waiting
        start_time = time.time()
        initial_image_state = image_SN2  # Remember what image_SN1 was at the start
        image_timeout = hlb.get_time_setting('ImageTimeout')
        
        self._io_log(2, "INFO", f"Waiting for new image. Current state: {initial_image_state}")

        # ---- wait for NEW image ----
        # FIX: Proper loop with three conditions:
        # 1. Wait while we haven't received a new image
        # 2. New image means: image_SN1 changed from initial_image_state
        # 3. AND image_SN1 is not None
        image_received = False
        your_s2_arrived_flag = False

        while not image_received and not self._stop_event.is_set():
            current_time = time.time()
            
            # Check if we got a new image
            if "ShelveColor" in di2:
                self._SN_Proccess2(self.client_Vision_station2_SN.send_request("I"))
                self._io_log(2, "INFO", f"doneeeeeeeeeeeeeeeeeeeeeeeeeeee{di2}")
                if image_SN2 is not None and image_SN2 != initial_image_state:
                    self._io_log(2, "INFO", f"New image received: {image_SN2}")
             
                
                    image_received = True
                    if queue is not None:
                        queue.task_done()
                    di2.clear()

            if current_time - start_time > image_timeout:
                self._io_log(2, "WARNING", f"S2 image timeout after {image_timeout} seconds")
                break

            # Wait a bit before checking again
            time.sleep(0.1)

        # ---- image received successfully ----
        last_image_SN2 = image_SN2
        self._io_log(2, "INFO", f"Image processing complete for: {image_SN2}")
    

    def data_processing_station1(self, test_results_dict):
                    global your_s1_result
                    self.client_scanner_station1._log_add("INFO", "Station 1 processing thread started")
         
            
                    self.client_scanner_station1._log_add("INFO", f"before the try block{test_results_dict}")

            #if test_results_dict: #and isinstance(test_results_dict, dict):                    
                    # 2. استخراج الاختبارات الفاشلة
                    zero_values_list = [k for k, v in test_results_dict.items() if v == "0"]
                    failed_tests = ", ".join(zero_values_list)
                    station_name = "VisionOuterTest"
                    if zero_values_list:

                        station_result = "FAIL" 
                    else :
                        station_result = "PASS" 

                    
                    # 3. سحب رقم الـ Dummy (تأكد أن الكيو ده فيه داتا فعلاً)
                    try:
                        dummy = self.client_scanner_station1.shared_queue2.get_nowait()

                        self.client_scanner_station1._log_add("INFO", f"before the uploooooooooooad block{test_results_dict}")
                        # 4. الرفع لقاعدة البيانات
                        db.upload_tests_result_to_db(
                            dummy=dummy,
                            station_name=station_name,
                            station_result=station_result,
                            failed_tests=failed_tests,
                            Client=self.client_scanner_station1
                        )
                        
                        self.client_scanner_station1._log_add("INFO", f"afteeeeeeeeeeeeeeeeeeeeeeer the uploaaaaaaaaaaaaad block{test_results_dict}")
                        # تأكيد إتمام المهمة للكيو الخاص بالـ dummy
                        self.client_scanner_station1.shared_queue2.task_done()
                    except:
                        dummy = queue_manual_FOR_Proessing.get_nowait()
                        
                        # 4. الرفع لقاعدة البيانات
                        db.upload_tests_result_to_db(
                            dummy=dummy,
                            station_name=station_name,
                            station_result=station_result,
                            failed_tests=failed_tests,
                            Client=self.client_scanner_station1)
                        self.client_scanner_station1._log_add("WARNING", "No dummy ID found in shared_queue2")

                    # تأكيد إتمام المهمة للكيو الخاص بالنتائج
                        queue_manual_FOR_Proessing.task_done()
                    global your_s1_failed_tests
                    your_s1_failed_tests = {
                        "dummy": str(dummy) if dummy is not None else "",
                        "result": station_result,
                        "tests": zero_values_list,
                    }
                    your_s1_result = station_result   
                    time.sleep(3)
                    your_s1_result = None
            
            



    def data_processing_station2(self, test_results_dict2):
                    global your_s2_result
                    self.client_scanner_station2._log_add("INFO", "Station 2 processing thread started")
         
                  #test_results_dict2 = {}
                    self.client_scanner_station2._log_add("INFO", "قبل التراااااي")
                              
                 # 2. استخراج الاختبارات الفاشلة
                    zero_values_list = [k for k, v in test_results_dict2.items() if v == "0"]
                    failed_tests = ", ".join(zero_values_list)
                    station_name = "VisionInnerTest"
                    if zero_values_list:

                        station_result = "FAIL" 
                    else :
                        station_result = "PASS" 
                    
                       
                    # 3. سحب رقم الـ Dummy (تأكد أن الكيو ده فيه داتا فعلاً)
                    try:
                        dummy = self.client_scanner_station2.shared_queue2.get_nowait()
                        
                        # 4. الرفع لقاعدة البيانات
                        db.upload_tests_result_to_db(
                            dummy=dummy,
                            station_name=station_name,
                            station_result=station_result,
                            failed_tests=failed_tests,
                            Client=self.client_scanner_station2
                        )
                        

                        # تأكيد إتمام المهمة للكيو الخاص بالـ dummy
                        self.client_scanner_station2.shared_queue2.task_done()
                    except:
                        dummy = queue_manual2_FOR_Proessing.get_nowait()
                        
                        # 4. الرفع لقاعدة البيانات
                        db.upload_tests_result_to_db(
                            dummy=dummy,
                            station_name=station_name,
                            station_result=station_result,
                            failed_tests=failed_tests,
                            Client=self.client_scanner_station2)
                        self.client_scanner_station2._log_add("WARNING", "No dummy ID found in shared_queue2")

                    # تأكيد إتمام المهمة للكيو الخاص بالنتائج
                        queue_manual2_FOR_Proessing.task_done()
                    global your_s2_failed_tests
                    your_s2_failed_tests = {
                        "dummy": str(dummy) if dummy is not None else "",
                        "result": station_result,
                        "tests": zero_values_list,
                    }
                    your_s2_result = station_result
                    time.sleep(3)  
                    your_s2_result = None
           
                    time.sleep(1) # عشان لو حصل خطأ متكرر ميعلقش الجهاز

    def auto_load_csv_by_product_number(self, product_number: str, part: str, server_instance , queue: queue): # type: ignore # server_instance = client intense
        """Automatically load CSV file based on ProductNumber"""
        global NO_CSV_ERROR, NO_CSV_ERROR2,Buzzer_Flag_to_OFF, Buzzer_Flag_to_OFF2
        global NO_CSV_FILE, NO_CSV_FILE2
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
            # مصدر واحد للمسار — الفولدر اتغير اسمه من CreateProgram\ إلى
            # Programs\ وده بيتبعه أوتوماتيك.
            csv_path  = os.path.join(hlb.CSV_SOURCE_DIR, filename)
        

            
            server_instance._log_add("INFO", f"Looking for CSV file: {filename}")
            
            while not os.path.isfile(csv_path):
                server_instance._log_add("WARNING", f"CSV file not found: {filename}")
                if part == "S1":
                    NO_CSV_ERROR = True
                    NO_CSV_FILE = filename
                    dummmy = self.client_scanner_station1.shared_queue2.get()  # سحب الـ dummy من الكيو الخاص بالـ dummy
                    dummy = self.client_scanner_station1.shared_queue3.get()  # سحب الـ dummy من الكيو الخاص بالـ dummy
                    self.client_scanner_station1.shared_queue2.task_done()  # تأكيد انتهاء المهمة للكيو الخاص بالـ dummy
                    self.client_scanner_station1.shared_queue3.task_done()  # تأكيد انتهاء المهمة للكيو الخاص بالـ dummy
                elif part == "S2":
                    NO_CSV_ERROR2 = True
                    NO_CSV_FILE2 = filename
                    dummmy = self.client_scanner_station2.shared_queue2.get()  # سحب الـ dummy من الكيو الخاص بالـ dummy
                    dummy = self.client_scanner_station2.shared_queue3.get()  # سحب الـ dummy من الكيو الخاص بالـ dummy
                    self.client_scanner_station2.shared_queue2.task_done()  # تأكيد انتهاء المهمة للكيو الخاص بالـ dummy
                    self.client_scanner_station2.shared_queue3.task_done()  # تأكيد انتهاء المهمة للكيو الخاص بالـ dummy
                #server = TCPClient(Ip_write_IO, Port_write_IO)
                if part == "S1":
                    self.client_write_io.send_request(generate_modbus_command("BUZZER_S1", "ON"), is_hex=True)
                if part == "S2":
                    self.client_write_io.send_request(generate_modbus_command("BUZZER_S2", "ON"), is_hex=True)

                while True:
                    if Buzzer_Flag_to_OFF:
                        self.client_write_io.send_request(generate_modbus_command("BUZZER_S1", "OFF"), is_hex=True)
                        break
                    
                    if Buzzer_Flag_to_OFF2:
                        self.client_write_io.send_request(generate_modbus_command("BUZZER_S2", "OFF"), is_hex=True)
                        break
                
                time.sleep(60)  # انتظر 60 ثانية قبل إعادة التحقق من وجود الملف

            # الملف اتلاقى -> نظّف اسم الملف المفقود
            if part == "S1":
                NO_CSV_FILE = None
            elif part == "S2":
                NO_CSV_FILE2 = None

            csv_data = hlb._load_csv_file(csv_path)
            
            # 1. الحصول على جميع العناوين (الأعمدة) من ملف الـ CSV
            # نفترض أن csv_data عبارة عن قاموس (Dictionary) يمثل الصف
            all_columns = list(csv_data.keys())
            
            # 2. تحديد الكلمة التي تريد البحث عنها لنقلها للآخر
            target_word = "Front Logo" # يمكنك تغييرها لما يناسبك أو جعلها متغيرًا
            target_word2 = "Shelve color"
            
        
            
                
            # 4&3. تجميع الكود بناءً على الترتيب الجديد
        
            if part == "S1":
                order = [col for col in all_columns if col != target_word]
            
                if target_word in all_columns:
                    order.append(target_word)
            else:
                order = [col for col in all_columns if col != target_word2]
            
                if target_word2 in all_columns:
                    order.append(target_word2)
                
            codes = "".join(_get_code(csv_data.get(k, "")) for k in order if _get_code(csv_data.get(k, "")) != "")
            
            server_instance.current_program_label = filename
            server_instance.current_program_data = csv_data
            
            server_instance._log_add("AUTO_LOAD", f"PRODUCT_NUMBER_CSV_LOADED_{part}: {filename} {codes}")
            server_instance._log_add("INFO", f"Auto-loaded program: {filename} with codes: {codes}")
            #codes= textwrap.wrap(codes, width=2)
            if part == "S1":
                self._vision_station_1(codes)
            if part == "S2":
                self._vision_station_2(codes)
            #queue.put(codes)
            #auto_send_codes(codes, filename, csv_data, part, server_instance)
            #return codes
        except Exception as e:
            server_instance._log_add("ERROR", f"Error in auto_load_csv_by_product_number: {e}")
    

   
    '''
#database handling
    def auto_connect_db(self):
        """Automatically connect to saved database settings"""
        global conn_str_db1_global, conn_str_db2_global
        conn_str_db1_global, msg1 = self.connect_from_file("last_db1_settings.txt", 1)
        conn_str_db2_global, msg2 = self.connect_from_file("last_db2_settings.txt", 2)
        print(f"{msg1}\n{msg2}")

    def connect_from_file(self, filename, index):
        if not os.path.exists(filename):
            return None, f"No saved DB{index} settings"
        with open(filename, "r") as f:
            data = f.read().strip().split("|")
            if len(data) != 5:
                return None, f"Invalid DB{index} format"
            serveraddr, database_name, Auth, user_name, password = data

        # نفس منطق db.build_conn_str — بيختار أحسن درايفر متاح
        try:
            conn_str = db.build_conn_str(
                serveraddr, database_name, Auth, user_name, password
            )
        except RuntimeError as e:
            return None, f"DB{index}: {e}"

        try:
            with pyodbc.connect(conn_str, timeout=15):
                pass
            return conn_str, f"Auto-connected to DB{index}"
        except Exception as e:
            return None, f"DB{index} connection failed: {e}"

    '''    

    def run(self):
        self.root.mainloop()

##################################################################





