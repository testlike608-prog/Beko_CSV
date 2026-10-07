from flask import Blueprint
from flask import render_template, request, redirect, url_for, session
from .decorators import login_required
import  os, csv
from datetime import timedelta # استورد دي في أول الملف


auth = Blueprint(
    "auth",
    __name__,
    template_folder="templates"
)

#-----------------check if logins.csv exist---------------
LOGINS_FILE = "logins.csv"
if not os.path.exists(LOGINS_FILE):
    with open(LOGINS_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Username", "Password", "Authentication"])
#----------------Function to check credentials from CSV-----------
def check_credentials(username, password):
    if os.path.exists(LOGINS_FILE):
        with open(LOGINS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                u = row.get("username") or row.get("Username") or row.get("USER") or ""
                p = row.get("password") or row.get("Password") or ""
                auth = row.get("auth") or row.get("Auth") or row.get("Authentication") or ""

                if u == username and p == password:
                    return auth  
    if username == "M.Ashraf" and password == "Beko2026":
        return "admin"
    if username == "Meeserv" and password == "meeserv@2026":
        return "dev"

    return None

#---------------------LOgin Function---------------------
@auth.route("/login", methods=["GET", "POST"])
def login():
    message = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # استلام قيمة الزرار (هيرجع True لو متعلم عليه)
        remember = request.form.get('remember_me') 

        auth = check_credentials(username, password)
        if auth:  
            session['username'] = username
            session['auth'] = auth
            
            # لو المستخدم اختار Remember Me، خلي السشن "دائمة"
            if remember:
                session.permanent = True
                # اختيارياً: حدد المدة (مثلاً 30 يوم)
                #app.permanent_session_lifetime = timedelta(days=30)
            else:
                # لو مفيش علامة، السشن هتموت بمجرد قفل المتصفح
                session.permanent = False
                
            return redirect(url_for('flash.loading'))
        else:
            return render_template("LOGIN_HTML.html", error="Invalid username or password")
            
    return render_template("LOGIN_HTML.html", error=None)