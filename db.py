import os, pyodbc
import subprocess
from typing import Protocol


class _SupportsLogAdd(Protocol):
    def _log_add(self, level: str, msg: str) -> None: ...


# مهلة الاتصال (ثواني). كانت 15 لكل قاعدة، يعني 30 ثانية انتظار لو
# السيرفرات مش موصولة. على شبكة محلية 5 ثواني أكتر من كفاية.
CONNECT_TIMEOUT = 5

conn_str_db1_global=""
conn_str_db2_global=""
global connected1, connected2
connected1=False
connected2 = False
# ----------------------------------------------------------------------
# اختيار درايفر ODBC
#
# الكود كان بيفترض "ODBC Driver 18 for SQL Server" دايمًا. لو مش متسطب،
# كل الاتصالات بتفشل — حتى لو فيه درايفر تاني شغال على الجهاز.
# دلوقتي بنختار أحسن درايفر *موجود فعلاً*، وبنبني الـ connection string
# حسب إمكانياته.
#
# مهم: الدرايفر القديم "SQL Server" (اللي جاي مع ويندوز) مش بيفهم
# Encrypt / TrustServerCertificate — لو بعتناهم ليه الاتصال بيرمي خطأ،
# عشان كده بنشيلهم في حالته.
# ----------------------------------------------------------------------
PREFERRED_DRIVERS = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "ODBC Driver 13.1 for SQL Server",
    "ODBC Driver 13 for SQL Server",
    "ODBC Driver 11 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server",           # آخر حل — قديم بس شغال
]

# الدرايفرات اللي بتفهم Encrypt / TrustServerCertificate
_MODERN_PREFIXES = ("ODBC Driver", "SQL Server Native Client")


def available_drivers():
    try:
        return list(pyodbc.drivers())
    except Exception:
        return []


def pick_driver():
    """أحسن درايفر متاح على الجهاز، أو None لو مفيش خالص."""
    installed = available_drivers()
    for name in PREFERRED_DRIVERS:
        if name in installed:
            return name
    return installed[0] if installed else None


def build_conn_str(serveraddr, database_name, auth, user_name, password, driver=None):
    driver = driver or pick_driver()
    if not driver:
        raise RuntimeError("مفيش أي ODBC driver متسطب على الجهاز")

    parts = [
        f"DRIVER={{{driver}}};",
        f"SERVER={serveraddr};",
        f"DATABASE={database_name};",
    ]

    if auth == "Windows Authentication":
        parts.append("Trusted_Connection=yes;")
    else:
        parts.append(f"UID={user_name};PWD={password};")

    if driver.startswith(_MODERN_PREFIXES):
        parts.append("Encrypt=no;TrustServerCertificate=yes;")

    return "".join(parts)


def check_driver():
    """هل فيه درايفر حديث (17/18)؟"""
    installed = available_drivers()
    return any(
        "ODBC Driver 17 for SQL Server" in d or "ODBC Driver 18 for SQL Server" in d
        for d in installed
    )


def install_driver():
    msi_path = os.path.join(os.path.dirname(__file__), "msodbcsql.msi")
    if not os.path.exists(msi_path):
        print(f"ODBC installer not found at {msi_path}")
        return False
    try:
        subprocess.run(["msiexec", "/i", msi_path, "/quiet", "/norestart"], check=True)
        print("ODBC Driver installed")
        return True
    except Exception as e:
        print(f"Installation failed: {e}")
        print("   ملحوظة: msiexec /quiet محتاج صلاحيات أدمن — "
              "افتح msodbcsql.msi يدويًا ووافق على UAC.")
        return False


if not check_driver():
    _fallback = pick_driver()
    if _fallback:
        # مش هنحاول نسطّب تلقائيًا طالما فيه درايفر شغال — التسطيب الصامت
        # محتاج أدمن وبيفشل من غير ما حد ياخد باله.
        print(f"ODBC Driver 17/18 not exists, using '{_fallback}' instead")
        print("  ( install ODBC Driver 18 x64 manually)")
    else:
        print("ODBC Driver not found on the system, attempting installation...")
        install_driver()

def auto_connect_db():
    """Automatically connect to saved database settings"""
    global conn_str_db1_global, conn_str_db2_global, connected1, connected2

    def connect_from_file(filename, index):
        if not os.path.exists(filename):
            return None, f"No saved DB{index} settings"
        with open(filename, "r") as f:
            data = f.read().strip().split("|")
            if len(data) != 5:
                return None, f"Invalid DB{index} format"
            serveraddr, database_name, Auth, user_name, password = data

        try:
            conn_str = build_conn_str(
                serveraddr, database_name, Auth, user_name, password
            )
        except RuntimeError as e:
            return None, f"DB{index}: {e}"

        try:
            with pyodbc.connect(conn_str, timeout=CONNECT_TIMEOUT):
                pass
            return conn_str, f"SUCCESSFUL Auto-connected to DB{index}"
        except Exception as e:
            return None, f"DB{index} connection failed: {e}"

    conn_str_db1_global, msg1 = connect_from_file("last_db1_settings.txt", 1)
    conn_str_db2_global, msg2= connect_from_file("last_db2_settings.txt", 2)
    print(f"{msg1}\n{msg2}")

def upload_tests_result_to_db(dummy, station_name, station_result, failed_tests, Client: _SupportsLogAdd):
    """
    Inserts a new record in DB2 (VisionResult table)
    with SFC, TESTNAME, RESULT, NCCODE columns.
    
    Args:
        dummy: The SFC/Dummy number
        station_name: Test name (e.g., VisionOuterTest, VisionInnerTest)
        station_result: Overall result (PASS/FAIL)
        failed_tests: Comma-separated string of failed test names
    """
    global conn_str_db2_global

    try:
        # Check DB connection string exists
        if not conn_str_db2_global:
            Client._log_add("ERROR", "No DB2 connection string found")
            return

        # Insert new row
        with pyodbc.connect(conn_str_db2_global, timeout=15) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO VisionResult (SFC, TESTNAME, RESULT, NCCODE)
                    VALUES (?, ?, ?, ?)
                    """,
                    (dummy, station_name, station_result, failed_tests)
                )
                conn.commit()
                Client._log_add("INFO",f"Uploaded to DB → SFC={dummy}, TestName={station_name}, Result={station_result}, FailedTests={failed_tests}")
               
                    
              
                
            except Exception as e:
                Client._log_add("ERROR", f"DB Insert Error: {e}")
                pass
    except Exception as ex:
        Client._log_add("ERROR", f"Error connecting to DB: {ex}")
        pass