# Docker — Step by Step

من البناء على جهازك، لحد التشغيل على جهاز العميل.

---

## STEP 0 — الاختبار اللي لازم يتعمل الأول (نص ساعة)

**متعملش الصورة كلها قبل ما تتأكد من ده.**

العميل عنده ترخيص VisionMaster — بس السؤال مش "عنده ترخيص ولا لأ"،
السؤال هو **هل الترخيص بيتفعّل جوه كونتينر؟**
تراخيص الأجهزة الصناعية غالبًا مربوطة بـ hardware ID أو دونجل USB،
والكونتينر بيشوف هاردوير مختلف عن الجهاز.

### اختبار سريع

اعمل ملف اسمه `Dockerfile.licencetest`:

```dockerfile
FROM mcr.microsoft.com/windows/servercore:ltsc2022
SHELL ["powershell", "-Command", "$ErrorActionPreference='Stop';"]
COPY VisionMaster-Setup.exe .
RUN Start-Process ./VisionMaster-Setup.exe -Wait -ArgumentList '/S'
CMD ["powershell"]
```

```powershell
docker build -f Dockerfile.licencetest -t vm-licencetest .
docker run -it --rm vm-licencetest
```

جوه الكونتينر، افتح أداة الترخيص بتاعة VisionMaster وشوف بتقول إيه.

| النتيجة | اعمل إيه |
|---|---|
| الترخيص متفعّل | كمّل من STEP 1 |
| الترخيص مرفوض / دونجل مش متلاقي | Docker مش هينفع — روح لـ PyInstaller (آخر الملف) |

لو الدونجل USB، جرّب `--device` أو USB passthrough — بس توقّع إنه مش هيشتغل
في Windows containers.

---

## STEP 1 — تجهيز جهازك

1. ويندوز 10/11 **Pro** أو Windows Server (الـ Home مبيدعمش containers)
2. سطّب **Docker Desktop**
3. كليك يمين على أيقونة Docker في شريط المهام →
   **Switch to Windows containers…**
   (لو مكتوب "Switch to Linux containers" يبقى إنت أصلاً في وضع ويندوز)
4. حط مثبّت VisionMaster جنب الـ `Dockerfile`

تأكد:
```powershell
docker version --format '{{.Server.Os}}'    # لازم يطلع: windows
```

---

## STEP 2 — تفعيل تسطيب VisionMaster في الـ Dockerfile

افتح `Dockerfile` وفي **الخطوة 4** شيل التعليق عن السطرين دول
وعدّل اسم الملف حسب المثبّت اللي عندك:

```dockerfile
COPY VisionMaster-Setup.exe .
RUN Start-Process ./VisionMaster-Setup.exe -Wait -ArgumentList '/S' ; \
    Remove-Item VisionMaster-Setup.exe
```

> `/S` هي أشهر صيغة للتسطيب الصامت. لو مشتغلتش جرّب `/quiet` أو `/silent`،
> أو شغّل المثبّت بـ `/?` عشان تشوف الاختيارات.

**كمان:** شيل مثبّت VisionMaster من `.dockerignore` لو حطيته هناك،
وإلا `COPY` مش هيلاقيه.

---

## STEP 3 — البناء

```powershell
cd D:\beko_api\beko
docker compose build
```

أول بناء بياخد **20-40 دقيقة** (بينزّل servercore ~5GB + Python + ODBC + VisionMaster).
اللي بعده أسرع بكتير بسبب الـ cache.

---

## STEP 4 — التشغيل والاختبار على جهازك

```powershell
docker compose up -d
docker compose logs -f
```

المفروض تشوف:
```
Web layer ready — press START in the UI to run the process.
ODBC driver in use: ODBC Driver 18 for SQL Server
Socket.IO tickers started
```

افتح `http://localhost:5000`

**تشيك على إيه:**

1. تقدر تسجّل دخول
2. الحالة بتتحدّث من غير refresh (يعني Socket.IO شغال)
3. ادخل بمستخدم **dev** → I/O Mapping → Browse → اختار ملف الـ solution
   *(المسارات دلوقتي جوه الكونتينر مش على جهازك)*
4. **اضغط START** — ودي اللحظة الحقيقية:
   ```
   [VisionMaster][INFO] Assemblies loaded.
   [VisionMaster][INFO] Loaded successfully: ...
   [VisionMaster][INFO] 2 flow(s) ready: ['Flow1', 'Flow2']
   [VisionMaster][INFO] [RUNNING] Flow1
   ```

لو وصلت لـ `[RUNNING]` يبقى الصورة سليمة.

---

## STEP 5 — حفظ الصورة في ملف

```powershell
docker save beko-vision:latest -o beko-vision.tar
```

الحجم هيبقى تقريبًا **6-9 GB**. اضغطه:

```powershell
Compress-Archive -Path beko-vision.tar -DestinationPath beko-vision.zip
```

(أو استخدم 7-Zip — بيضغط أحسن بكتير للملفات دي)

---

## STEP 6 — النقل للعميل

اختار اللي يناسبك:

**(أ) هارد / فلاشة** — الأبسط للملفات الكبيرة دي

**(ب) رفع على مساحة تخزين** (OneDrive / Google Drive / FTP)

**(ج) Docker registry** — لو فيه شبكة بينكم:
```powershell
# عندك
docker tag beko-vision:latest myregistry.local:5000/beko-vision:1.0
docker push myregistry.local:5000/beko-vision:1.0

# عند العميل
docker pull myregistry.local:5000/beko-vision:1.0
```

**ابعت معاه كمان:**
- `docker-compose.yml`
- `config.json` (بالماپينج الصح)
- `logins.csv` (المستخدمين)
- مجلد `CreateProgram/` (برامج الـ CSV)

---

## STEP 7 — التشغيل على جهاز العميل

### 7.1 تجهيز الجهاز (مرة واحدة بس)

1. ويندوز 10/11 **Pro** أو Windows Server
2. سطّب **Docker Desktop**
3. **Switch to Windows containers**

### 7.2 تحميل الصورة

```powershell
docker load -i beko-vision.tar
docker images        # تأكد إن beko-vision ظهرت
```

### 7.3 تجهيز الملفات

اعمل مجلد، مثلاً `C:\beko`، وحط فيه:
```
C:\beko\
  docker-compose.yml
  config.json
  logins.csv
  data\
  CreateProgram\
```

### 7.4 التشغيل

```powershell
cd C:\beko
docker compose up -d
```

افتح `http://localhost:5000`

### 7.5 التشغيل التلقائي مع الويندوز

`restart: unless-stopped` موجودة أصلاً في الـ compose، فالكونتينر
بيرجع لوحده بعد أي restart طالما Docker Desktop بيفتح مع الويندوز
(من إعدادات Docker → General → *Start Docker Desktop when you log in*).

---

## الشبكة — تشيك سريع

| الجهاز | العنوان | شغال في الكونتينر؟ |
|---|---|---|
| Scanner S1 / S2 | 192.168.1.16 / .17 | اتصال خارج، NAT عادي |
| I/O module | 192.168.1.30:502 | نفس الكلام |
| VisionMaster | 127.0.0.1:20/30/40/50 | **طالما VisionMaster جوه الصورة** |
| cam_cap | 127.0.0.1:70/80 | نفس الكلام |
| SQL Server | حسب إعدادات العميل | لو الجهاز شايفه |

> لو VisionMaster **مش** جوه الصورة، كل عناوين `127.0.0.1` هتفشل
> لأنها وقتها بتشاور على الكونتينر نفسه. وده اللي خلانا نسطّبه جواه.

لو الكونتينر مش شايف `192.168.1.x`، جرّب:
```yaml
network_mode: "host"      # في الـ compose
```

---

## التحديث بعدين

```powershell
# عندك
docker compose build
docker save beko-vision:latest -o beko-vision-v2.tar

# عند العميل
docker compose down
docker load -i beko-vision-v2.tar
docker compose up -d
```

`config.json` و `logins.csv` و `data/` و `CreateProgram/` كلها volumes،
يعني **مش بتتمسح** مع التحديث.

---

## أوامر بتحتاجها

```powershell
docker compose logs -f            # اللوج
docker compose restart            # إعادة تشغيل
docker compose down               # إيقاف
docker exec -it beko-vision powershell   # دخول جوه الكونتينر
docker stats beko-vision          # استهلاك الرام والمعالج
```

---

## لو الترخيص مرفض جوه الكونتينر → PyInstaller

لو STEP 0 فشل، Docker مش هينفع للمشروع ده. البديل:

```powershell
pip install pyinstaller
pyinstaller --noconfirm --name beko --onedir main_fastapi.py `
  --add-data "templates;templates" `
  --add-data "static;static" `
  --hidden-import uvicorn.logging `
  --hidden-import uvicorn.loops.auto `
  --hidden-import uvicorn.protocols.http.auto `
  --hidden-import engineio.async_drivers.asgi
```

بيطلع مجلد `dist\beko\` تنسخه على جهاز العميل ويشتغل بـ `beko.exe`.
بيشتغل native، يعني VisionMaster والترخيص شغالين زي ما هما بالظبط،
والحجم بالميجابايت مش الجيجابايت.

الكود متجهّز لكده أصلاً (`sys.frozen` متعامَل معاه في `main_fastapi.py`
و `fastapi_app/core.py`). قوللي وأنا أظبطه بالكامل وأختبره.
