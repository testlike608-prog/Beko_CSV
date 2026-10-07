# Socket.IO — خطوات التركيب (جهاز أوفلاين)

الكود جاهز، بس محتاج حاجتين على جهاز الخط قبل ما يشتغل.
**لو الاتنين مش موجودين، التطبيق هيشتغل عادي وهيرجع للـ polling القديم أوتوماتيكيًا** — مفيش حاجة هتتكسر.

---

## 1. مكتبة البايثون

على أي جهاز فيه إنترنت:

```
pip download python-socketio -d socketio_pkgs
```

انقل مجلد `socketio_pkgs` لجهاز الخط وسطّب منه:

```
pip install --no-index --find-links socketio_pkgs python-socketio
```

للتأكد:

```
python -c "import socketio; print(socketio.__version__)"
```

> ملحوظة: `python-socketio` بيجيب معاه `python-engineio` و `bidict`.
> مش محتاج `aiohttp` — إحنا شغالين ASGI عن طريق uvicorn.

---

## 2. ملف الجافاسكريبت

نزّل نسخة **الإصدار 4** من الكلاينت:

```
https://cdn.socket.io/4.7.5/socket.io.min.js
```

وحطه في:

```
D:\beko_api\beko\static\socket.io.min.js
```

**مهم:** لازم يكون الإصدار 4.x عشان يتوافق مع `python-socketio` الحديث.

---

## 3. التأكد إنه اشتغل

بعد إعادة تشغيل `main_fastapi.py` هتلاقي في الكونسول:

```
Socket.IO tickers started
```

لو المكتبة ناقصة هتلاقي بدلها:

```
python-socketio غير متسطب — الواجهة هترجع للـ polling
```

---

## اللي اتغيّر

| قبل | بعد |
|---|---|
| `/process/status` كل ثانيتين (من مكانين) | حدث `process_status` عند التغيير |
| `/station1_status` + `/station2_status` كل ثانية | `station1` / `station2` عند التغيير |
| `/check-flags` + `/check-flags2` كل ثانية | `flags1` / `flags2` عند التغيير |
| `/sql_status` كل ثانيتين **لكل تاب** | `sql_status` كل 5 ثواني لكل السيرفر |

كل الـ REST endpoints القديمة **لسه موجودة** وشغالة — مستخدمة كـ fallback،
وكمان الأوامر (START/STOP، حفظ الإعدادات، الفورمز) لسه بتمشي على REST زي ما هي.

### نقطتين مهمين في التنفيذ

1. **`Buzzer_Flag_to_OFF`** — الـ endpoint القديم `/check-flags` مكانش قراءة بس،
   كان بيعمل `cc.Buzzer_Flag_to_OFF = False` في كل نداء، واللوب في
   `ClientsClass.auto_load_csv_by_product_number` معتمد على ده عشان يطفي الجرس.
   عشان كده الـ ticker بتاع الفلاجات شغال بنفس المعدل (ثانية) وبيعمل نفس
   الـ reset. أي تغيير في المعدل ده بيأثر على الجرس.

2. **`sql_status`** — بيفتح اتصال `pyodbc` حقيقي بـ `timeout=2`، فبيتنفذ
   جوه `asyncio.to_thread` عشان ما يقفلش الـ event loop على باقي العملاء.
