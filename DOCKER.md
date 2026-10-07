# تشغيل المشروع في Docker (Windows containers)

## قبل أي حاجة — اقرأ ده

الصورة دي **صورة ويندوز**، مش لينكس. على جهاز العميل لازم:

- ويندوز 10/11 Pro أو Windows Server
- Docker Desktop، وميوده على **Windows containers**
  (كليك يمين على أيقونة Docker في شريط المهام → *Switch to Windows containers*)

سبب ده إن VisionMaster اسمبليز .NET بتتحمّل بـ pythonnet، ومفيش ليها
مقابل على لينكس — وكمان سيرفراته شغالة على `127.0.0.1`.

---

## الوضع الحالي: إيه اللي شغال وإيه اللي محتاج قرار

| الجزء | جوه الكونتينر؟ |
|---|---|
| واجهة الويب (FastAPI + Socket.IO) | شغال |
| قاعدة البيانات (pyodbc + ODBC 18) | شغال — الدرايفر بيتسطب في الصورة |
| السكانرات و I/O module (192.168.1.x) | شغال — عن طريق الشبكة عادي |
| **VisionMaster SDK** | محتاج قرار — اقرأ تحت |
| **سيرفرات vision على 127.0.0.1** | محتاج تعديل — اقرأ تحت |

---

## نقطة (1): ترخيص VisionMaster

مش بنقدر نحط مثبّت VisionMaster في الصورة — منتج مرخّص ومينفعش يتوزّع.
وقدامك طريقتين، والاتنين محتاجين تأكيد:

**(أ) تسطيب VisionMaster جوه الصورة**
حط المثبّت جنب الـ Dockerfile وفعّل السطرين في *الخطوة 4*.

> **لازم تتأكد من Hikrobot إن ترخيص VisionMaster بيتفعّل جوه Windows container.**
> أغلب تراخيص الأجهزة الصناعية مربوطة بالـ hardware ID أو دونجل USB،
> وده غالبًا مش بيشتغل جوه كونتينر. **دي أكبر مخاطرة في الخطة كلها**،
> ويستحسن تتأكد منها قبل ما تكمّل شغل.

**(ب) تركيب مجلد VisionMaster من الجهاز**
```
docker run -v "C:\Program Files\VisionMaster4.4.0:C:\VisionMaster:ro" ...
```
أخف بكتير، بس تسجيل COM ومفاتيح الريجستري بتفضل على الجهاز مش جوه
الكونتينر، فـ `VmSolution.Load` ممكن يفشل. يستاهل تجربة سريعة.

---

## نقطة (2): سيرفرات vision على 127.0.0.1

في `ClientsClass.py` المسارات دي متكتوبة ثابتة:

```python
Ip_vision_inner = "127.0.0.1"   # port 30
Ip_vision_outer = "127.0.0.1"   # port 20
Ip_vision_inner_SN = "127.0.0.1"  # port 50
Ip_vision_outer_SN = "127.0.0.1"  # port 40
self.cam_cap_s1 = TCPClient("127.0.0.1", 70)
self.cam_cap_s2 = TCPClient("127.0.0.1", 80)
```

جوه الكونتينر `127.0.0.1` هو **الكونتينر نفسه**، مش الجهاز.
فلو VisionMaster شغال على الجهاز، العناوين دي كلها هتفشل.

الحل إنها تبقى قابلة للتعديل وتشاور على `host.docker.internal`.
الـ compose بيبعت `BEKO_VISION_HOST` جاهزة، بس **الكود لسه مقراهاش** —
قوللي وأنا أعدّل `ClientsClass.py` تقراها مع الإبقاء على `127.0.0.1`
كقيمة افتراضية، فمفيش حاجة هتتغيّر على التسطيب العادي.

---

## البناء والتشغيل

```powershell
docker compose build
docker compose up -d
docker compose logs -f
```

الواجهة على `http://localhost:5000`.

## مشاركة الصورة مع العميل

```powershell
docker save beko-vision:latest -o beko-vision.tar
```

العميل يعمل:
```powershell
docker load -i beko-vision.tar
docker compose up -d
```

> صور ويندوز كبيرة — servercore لوحدها حوالي 5 GB مضغوطة.
> لو الحجم مشكلة، الحل الأنسب للتوزيع هو PyInstaller (شوف تحت).

---

## البيانات اللي بتفضل

الملفات دي متركّبة كـ volumes عشان التحديث ما يمسحهاش:

- `data/` — المخرجات ووقت التشغيل
- `CreateProgram/` — برامج الـ CSV
- `config.json` — ماپينج الـ I/O ومسارات VisionMaster
- `logins.csv` — المستخدمين

وكمان موجودة في `.dockerignore` عشان ما تتنسخش جوه الصورة أصلاً.

---

## بديل: PyInstaller

لو الترخيص مش هيعدّي جوه كونتينر (وده احتمال كبير)، الطريقة الأنسب
لتسليم العميل هي PyInstaller. الكود **أصلاً متجهّز لكده**:

```python
# main_fastapi.py و fastapi_app/core.py
if getattr(sys, "frozen", False):
    return os.path.normpath(os.path.dirname(sys.executable))
```

المميزات:
- مجلد واحد يتنسخ على الـ IPC — من غير Python ولا pip
- بيشتغل native فـ VisionMaster و `127.0.0.1` شغالين زي ما هما بالظبط
- حجم بالميجابايت مش الجيجابايت
- مفيش أي سؤال عن الترخيص

قوللي وأنا أظبط ملف الـ build.
