# =====================================================================
# Beko Refrigerator Vision System — Windows container image
#
# مهم جدًا: دي صورة *ويندوز*، مش لينكس.
# لازم تتبني وتشتغل على ويندوز مع Docker في وضع Windows containers
# (كليك يمين على أيقونة Docker Desktop -> "Switch to Windows containers").
#
# ليه ويندوز؟
#   - VisionMaster عبارة عن اسمبليز .NET بتتحمّل عن طريق pythonnet،
#     ومفيش ليها مقابل على لينكس.
#   - سيرفرات VisionMaster شغالة على 127.0.0.1 بورت 20/30/40/50،
#     و cam_cap على 70/80. جوه كونتينر لينكس، 127.0.0.1 هو الكونتينر
#     نفسه مش الجهاز، فكانت هتبقى غير قابلة للوصول.
#
# اقرأ DOCKER.md الأول — فيه نقطة الترخيص اللي لازم تتأكد منها.
# =====================================================================

# ltsc2022 لازم يطابق نسخة ويندوز على جهاز العميل (أو استخدم Hyper-V isolation)
FROM mcr.microsoft.com/windows/servercore:ltsc2022

SHELL ["powershell", "-Command", "$ErrorActionPreference='Stop';"]

# ---------------------------------------------------------------------
# 1. Python 3.11 (64-bit) — لازم 64-bit عشان pyodbc و pythonnet
# ---------------------------------------------------------------------
ARG PYTHON_VERSION=3.11.9
RUN Invoke-WebRequest -Uri \
      \"https://www.python.org/ftp/python/$env:PYTHON_VERSION/python-$env:PYTHON_VERSION-amd64.exe\" \
      -OutFile python-installer.exe ; \
    Start-Process python-installer.exe -Wait -ArgumentList \
      '/quiet','InstallAllUsers=1','PrependPath=1','Include_test=0' ; \
    Remove-Item python-installer.exe

# ---------------------------------------------------------------------
# 2. Microsoft ODBC Driver 18 for SQL Server
#    من غيره كل اتصالات pyodbc بتفشل (نفس المشكلة اللي قابلتنا على الجهاز)
# ---------------------------------------------------------------------
RUN Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/?linkid=2249006' \
      -OutFile msodbcsql.msi ; \
    Start-Process msiexec.exe -Wait -ArgumentList \
      '/i','msodbcsql.msi','/quiet','/norestart','IACCEPTMSODBCSQLLICENSETERMS=YES' ; \
    Remove-Item msodbcsql.msi

# ---------------------------------------------------------------------
# 3. مكتبات بايثون
# ---------------------------------------------------------------------
WORKDIR C:/app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip ; \
    python -m pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------
# 4. VisionMaster  ← الخطوة اللي محتاجة قرار منك
#
#    مش بنقدر نحط مثبّت VisionMaster في الصورة دي — منتج مرخّص
#    ومينفعش يتوزّع. عندك اختيارين:
#
#    (أ) تسطّبه جوه الصورة: حط المثبّت جنب الـ Dockerfile وفعّل السطرين دول.
#        لازم تتأكد الأول من Hikrobot إن الترخيص بيتفعّل جوه كونتينر.
#
#        COPY VisionMaster-Setup.exe .
#        RUN Start-Process ./VisionMaster-Setup.exe -Wait -ArgumentList '/S' ; \
#            Remove-Item VisionMaster-Setup.exe
#
#    (ب) تركبه من الجهاز وقت التشغيل (شوف DOCKER.md):
#        docker run -v \"C:\\Program Files\\VisionMaster4.4.0:C:\\VisionMaster:ro\" ...
#        الطريقة دي أخف بس الترخيص/تسجيل COM ساعات مبيشتغلش من mount.
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# 5. كود التطبيق
# ---------------------------------------------------------------------
COPY . .

# البيانات اللي بتتغيّر وقت التشغيل بتتحط في volumes عشان تفضل
# بعد أي تحديث للصورة (شوف docker-compose.yml)
VOLUME ["C:/app/data", "C:/app/CreateProgram"]

EXPOSE 5000

# مش بنستخدم main_fastapi.py لأنه بيحاول يفتح متصفح — مفيش متصفح
# جوه الكونتينر. بنشغّل uvicorn على طول.
# ملحوظة: fastapi_app.app:app هو التطبيق الملفوف بـ Socket.IO.
CMD ["python", "-m", "uvicorn", "fastapi_app.app:app", "--host", "0.0.0.0", "--port", "5000"]
