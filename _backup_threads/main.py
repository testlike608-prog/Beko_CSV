import webbrowser 
import threading 
import sys
import os

from flask import Flask,redirect
from auth import auth
from flash import flash
from home import home 
from SQL import SQL
from Manual import Manual
from CreateUser import CreateUser
from CreateProgram import CreateProgram
from ClientsClass import App
import db 
from waitress import serve
from ioSetting import io_mapping_bp
from time_setting import time_settings_bp   
from flags import flags


def _application_directory():
    """Project root: source tree when running .py; Nuitka/PyInstaller dist folder when frozen."""
    # Nuitka مبيحطش sys.frozen — بيحط __compiled__ في الموديول
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        return os.path.normpath(os.path.dirname(sys.executable))
    return os.path.normpath(os.path.dirname(os.path.abspath(__file__)))


APP_ROOT = _application_directory()

app = Flask(
    __name__,
    template_folder=os.path.join(APP_ROOT, "templates"),
    static_folder=os.path.join(APP_ROOT, "static"),
)
app.secret_key = "your-secret-key-here"


# نفس الـ cache busting بتاع نسخة FastAPI — القوالب مشتركة بين النسختين،
# فلازم الـ global ده يبقى موجود هنا كمان وإلا القوالب هترمي UndefinedError.
def _static_v(filename: str) -> str:
    try:
        return str(int(os.path.getmtime(os.path.join(APP_ROOT, "static", filename))))
    except OSError:
        return "0"


app.jinja_env.globals["static_v"] = _static_v

app.register_blueprint(auth) # login app
app.register_blueprint(flash) #splash page
app.register_blueprint(time_settings_bp) # تسجيل بلو برينت time_settings
app.register_blueprint(home) #index
app.register_blueprint(CreateProgram) #create program App
app.register_blueprint(CreateUser) #create User App
app.register_blueprint(SQL)
app.register_blueprint(Manual)
app.register_blueprint(io_mapping_bp) # تسجيل بلو برينت io_mapping
app.register_blueprint(flags) # تسجيل بلو برينت flags


@app.route("/")
def log():
    return redirect("/login")  

def main():
    ClientsApp = App()   
    ClientsApp.Start_connetion()
    threading.Thread(target= ClientsApp._IO_read, daemon= True).start()
    threading.Thread(target=ClientsApp._vision_station_2, daemon= True).start()
    threading.Thread(target=ClientsApp._vision_station_1, daemon= True).start()
    #threading.Thread(target=ClientsApp.data_processing_station1, daemon= True).start()
    #threading.Thread(target=ClientsApp.data_processing_station1, daemon=True).start()


if __name__ == "__main__":
    os.chdir(APP_ROOT)

    if not os.path.exists("data"):
        os.makedirs("data")
    db.auto_connect_db()
    threading.Timer(1, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    threading.Thread(target=main, daemon= True).start()
    #threading.Thread(target=app.run(debug=False), daemon= True).start()
    
    #app.run(debug= False)
    serve(app,host="0.0.0.0",port=5000)
    