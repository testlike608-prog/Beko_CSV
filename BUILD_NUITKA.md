# البناء بـ Nuitka وتسليمه للعميل

الطريقة دي بتطلع **مجلد واحد** العميل ينسخه على الـ IPC ويشغّله.
بيشتغل native، يعني:

- VisionMaster والترخيص شغالين زي ما هما — مفيش سؤال كونتينر
- `127.0.0.1:20/30/40/50` و `cam_cap` على 70/80 شغالين من غير أي تعديل كود
- السكانرات والـ I/O module عادي
- الحجم بالميجابايت مش الجيجابايت
- مفيش Docker ولا Python ولا pip على جهاز العميل

---

## تعديل مهم اتعمل في الكود

Nuitka **مبيحطش** `sys.frozen` (ده بتاع PyInstaller) — بيحط `__compiled__`
في كل موديول متكمبايل.

الكود كان بيتحقق من `sys.frozen` بس في 3 أماكن، يعني مع Nuitka كان
هيقع على الفرع الغلط ويحسب مسار المشروع من `__file__`.
وفي `fastapi_app/core.py` السطر ده:

```python
os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

كان هيطلع مستويين فوق ويخرج **بره مجلد الـ dist** — يعني `config.json`
و `logins.csv` و `templates/` مكانوش هيتلاقوا.

اتظبط في:
- `main_fastapi.py`
- `fastapi_app/core.py`
- `main.py`

دلوقتي بيتحقق من الاتنين: `sys.frozen` **أو** `__compiled__`.

---

## STEP 1 — تجهيز جهازك (مرة واحدة)

```powershell
pip install nuitka
```

Nuitka محتاج كومبايلر C. أول ما تشغّله هينزّل MinGW64 لوحده
(علشان كده حاطين `--assume-yes-for-downloads` في السكربت).
لو عندك Visual Studio متسطب هيستخدمه.

---

## STEP 2 — البناء

```powershell
cd D:\beko_api\beko
.\build_nuitka.bat
```

أول بناء **15-40 دقيقة** (pandas و uvicorn كبار). اللي بعده أسرع.

الناتج:
```
dist\main_fastapi.dist\
    main_fastapi.exe
    templates\
    static\
    config.json
    ... (الـ DLLs والمكتبات)
```

---

## STEP 3 — تكملة المجلد

انسخ الملفات دي **جنب `main_fastapi.exe`**:

```
dist\main_fastapi.dist\
    config.json                  ← الماپينج ومسارات VisionMaster
    logins.csv                   ← المستخدمين
    last_db1_settings.txt        ← إعدادات قاعدة البيانات (لو موجودة)
    last_db2_settings.txt
    Programs\                    ← برامج الـ CSV (البرنامج بيعمله لوحده)
    data\                        ← ممكن يبقى فاضي، التطبيق بيعمله لوحده
    msodbcsql.msi                ← درايفر ODBC (شوف تحت)
```

> **مهم للـ IPC:** أجهزة الخطوط غالبًا من غير إنترنت. حط `msodbcsql.msi`
> (موجود أصلاً في مجلد المشروع) جوه مجلد التسليم، عشان العميل ما يحتاجش
> ينزّل حاجة. من غيره كل اتصالات قاعدة البيانات هتفشل، والخط هيقع في
> مسار "مفيش CSV" وهيرن الجرس.

> ليه جنب الـ exe بالظبط؟ لأن `_application_directory()` بترجع
> `os.path.dirname(sys.executable)` وقت التجميد، والتطبيق بيعمل
> `os.chdir` عليها. فكل المسارات النسبية بتتحسب من هناك.

---

## STEP 4 — الاختبار على جهازك قبل ما تبعت

```powershell
cd dist\main_fastapi.dist
.\main_fastapi.exe
```

**تشيك على:**

1. الكونسول بيقول:
   ```
   Web layer ready — press START in the UI to run the process.
   ODBC driver in use: ODBC Driver 18 for SQL Server
   Socket.IO tickers started
   ```
2. المتصفح بيفتح لوحده على `http://127.0.0.1:5000`
3. تسجيل الدخول شغال (يعني `logins.csv` اتلاقى)
4. الحالة بتتحدّث من غير refresh (Socket.IO)
5. دخول بمستخدم **dev** → I/O Mapping → المسارات ظاهرة (`config.json`)
6. **اضغط START**:
   ```
   [VisionMaster][INFO] Assemblies loaded.
   [VisionMaster][INFO] 2 flow(s) ready: ['Flow1', 'Flow2']
   [VisionMaster][INFO] [RUNNING] Flow1
   ```

لو 6 اشتغلت، يبقى pythonnet اتجمّع صح — ودي أكتر نقطة فيها احتمال مشاكل.

---

## STEP 5 — التسليم للعميل

اضغط المجلد:

```powershell
Compress-Archive -Path dist\main_fastapi.dist -DestinationPath beko-vision-v2.zip
```

ابعته بأي طريقة (فلاشة / شبكة / لينك). الحجم المتوقع **150-400 MB**.

### على جهاز العميل

1. فك الضغط في مكان ثابت، مثلاً `C:\beko\`
2. دبل كليك على `msodbcsql.msi` (اللي جوه المجلد) ووافق على UAC —
   مرة واحدة بس، ومحتاجة صلاحيات أدمن
3. اتأكد إن **VisionMaster** متسطب ومرخّص (عنده أصلاً)
4. دبل كليك على `main_fastapi.exe`

مفيش Python، مفيش pip، مفيش Docker، ومفيش إنترنت.

### التشغيل مع بداية الويندوز

على جهاز خط إنتاج ده مهم — التطبيق لازم يرجع لوحده بعد أي إعادة تشغيل
أو انقطاع كهربا.

اعمل shortcut لـ `main_fastapi.exe`، بعدين اكتب في Run:
```
shell:startup
```
وحط الـ shortcut في المجلد اللي هيفتح.

> ملحوظة: مجلد الـ Startup بيشتغل بعد تسجيل الدخول. لو الـ IPC بيشتغل
> من غير ما حد يسجّل دخول، اعمل Scheduled Task بـ trigger
> "At startup" و "Run whether user is logged on or not".

---

## التحديثات بعدين

ابني تاني، وابعت المجلد الجديد. قول للعميل يحتفظ بالملفات دي
من النسخة القديمة:

- `config.json`
- `logins.csv`
- `last_db1_settings.txt` / `last_db2_settings.txt`
- `Programs\` (اختياري — البرنامج بيعمله أول تشغيل)
- `data\`

---

## لو حصلت مشاكل

**`ModuleNotFoundError` وقت التشغيل**
Nuitka مالقاش import ديناميكي. زوّد السطر ده في `build_nuitka.bat`:
```
--include-module=اسم_الموديول ^
```

**VisionMaster مبيحمّلش (`clr` / pythonnet)**
`clr_loader` بيشيل معاه ملفات runtime. لو فشل، جرّب تزوّد:
```
--include-package-data=pythonnet ^
```
ولو فضل بيفشل، سيب `pythonnet` بره الكومبايل:
```
--nofollow-import-to=clr ^
```
وسطّب `pythonnet` بشكل عادي جنب الـ exe.

**الأنتي فيرس بيمسك الـ exe**
عادي مع الملفات المبنية. ضيف استثناء، أو وقّع الملف بشهادة code signing.

**البناء بيفشل بسبب الكومبايلر**
سطّب Visual Studio Build Tools ومعاه "Desktop development with C++".
