# رفع المشروع على GitHub وبناء الـ EXE أوتوماتيك

---

## الأول خالص — الأسرار

في المجلد ملفات **ممنوع** تروح GitHub:

| الملف | فيه إيه |
|---|---|
| `logins.csv` | أسماء مستخدمين وباسوردات |
| `last_db1_settings.txt` | باسورد SQL بصيغة نص عادي |
| `last_db2_settings.txt` | نفس الكلام |
| `SQL/last_db1_settings.txt` | نسخة تانية |
| `SQL/last_db2_settings.txt` | نسخة تانية |

`.gitignore` بيمنعهم من دلوقتي، **بس ده مش بيشيلهم لو كانوا اترفعوا قبل كده.**

### اتأكد إنهم مش متتبعين

```powershell
cd D:\beko_api\beko
git ls-files | Select-String "logins.csv|last_db"
```

- **مفيش نتيجة** → تمام، كمّل عادي
- **طلعت نتايج** → الملفات دي متتبعة، شيلها من التتبع:

```powershell
git rm --cached logins.csv last_db1_settings.txt last_db2_settings.txt
git rm --cached SQL/last_db1_settings.txt SQL/last_db2_settings.txt
git commit -m "Stop tracking secret files"
```

> **مهم:** لو كانوا اتعملهم commit قبل كده، هيفضلوا موجودين في **الهيستوري**
> وأي حد يقدر يشوفهم. لو الريبو هيبقى public أو فيه ناس تانية، غيّر
> الباسوردات دي، أو نضّف الهيستوري بـ
> [git-filter-repo](https://github.com/newren/git-filter-repo).

---

## STEP 1 — أول رفع

الريبو موجود أصلاً (`.git` موجود). ضيف الملفات الجديدة:

```powershell
cd D:\beko_api\beko
git add .gitignore .github/ *.md build_nuitka.bat requirements.txt
git add fastapi_app/ static/ templates/ *.py
git commit -m "Add Nuitka build, CI workflow, and gitignore"
```

اعمل ريبو جديد على GitHub (**Private** يفضّل)، وبعدين:

```powershell
git remote add origin https://github.com/<اسمك>/beko-vision.git
git branch -M main
git push -u origin main
```

> لو `origin` موجود أصلاً: `git remote set-url origin <الرابط>`

---

## STEP 2 — بناء الـ EXE على GitHub

الوورك فلو موجود في `.github/workflows/build-exe.yml`، وبيشتغل على
**ويندوز** (لازم، عشان pythonnet و pyodbc).

### تشغيل يدوي

1. افتح الريبو على GitHub → تبويب **Actions**
2. اختار **Build Windows EXE** من الشمال
3. اضغط **Run workflow** → **Run workflow**
4. استنى (أول مرة ~30 دقيقة، بعد كده ~5 دقايق بفضل الكاش)
5. من صفحة الـ run، نزّل **beko-vision-windows** من قسم Artifacts

### إصدار رسمي للعميل

```powershell
git tag v1.0.0
git push origin v1.0.0
```

ده بيعمل **Release** تلقائي فيه ملف zip جاهز، مع خطوات التسطيب.
ابعت للعميل لينك الـ Release وخلاص.

---

## نقطة مهمة عن VisionMaster

الـ runner بتاع GitHub **مفيهوش VisionMaster** — وده مش مشكلة:

`vision_master.py` بيعمل `import clr` **جوه `load_vm()`** مش على مستوى
الملف، يعني وقت التشغيل مش وقت البناء. فالكومبايل بينجح عادي.

بس معناها إن **الـ EXE اللي طالع من GitHub لازم يتجرّب على جهاز فيه
VisionMaster متسطب** قبل ما يروح للعميل. الـ CI بيتأكد إنه *بيتبني*،
مش إن VisionMaster بيشتغل.

---

## الأسعار

| الريبو | التكلفة |
|---|---|
| Public | مجاني بالكامل |
| Private | 2000 دقيقة/شهر مجانًا، **بس ويندوز بيتحسب × 2** |

يعني بناء 30 دقيقة على ويندوز = 60 دقيقة من رصيدك.
الكاش بيخلّيها ~5 دقايق (10 من الرصيد)، فعادي جدًا.

---

## أوامر يومية

```powershell
git status                      # إيه اللي اتغيّر
git add -A                      # ضيف كل حاجة (الـ gitignore بيحمي الأسرار)
git commit -m "رسالة"
git push

git tag v1.0.1 && git push origin v1.0.1   # إصدار جديد
```

---

## لو البناء فشل على GitHub

افتح الـ run من تبويب Actions واقرا اللوج. أشهر الأسباب:

**`ModuleNotFoundError` وقت البناء**
مكتبة ناقصة في `requirements.txt`. ضيفها واعمل push.

**Nuitka بيفشل على pythonnet / clr_loader**
شوف قسم "لو حصلت مشاكل" في `BUILD_NUITKA.md` — فيه بدائل جاهزة.

**البناء بياخد وقت طويل جدًا**
الكاش بيتبني أول مرة بس. الـ run اللي بعده أسرع بكتير.

**فشل بسبب ملف ناقص**
اتأكد إن الملف مش متشال في `.gitignore` بالغلط. الـ runner بياخد
اللي في الريبو بس — أي ملف محلي مش مرفوع مش هيبقى موجود عنده.
