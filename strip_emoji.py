"""
strip_emoji.py
--------------
بيشيل كل الإيموجي من ملفات المشروع.

ليه؟ الـ console بتاع ويندوز بيبقى cp1252، وأي print فيه إيموجي
بيرمي UnicodeEncodeError وبيقتل الـ startup (زي اللي حصل في
realtime.start_tickers وخلّى السيرفر يخرج بـ exit code 3).

الاستخدام:
    python strip_emoji.py            # معاينة بس - مش بيكتب أي حاجة
    python strip_emoji.py --apply    # بينفّذ التعديل فعلاً

مهم:
  * العربي مش بيتمس - بنشيل الإيموجي والرموز التصويرية بس.
  * الأسهم (-> <-) والشرطة الطويلة مش بتتشال، لأنها جزء من الجُمل.
  * بعد ما بنشيل الإيموجي بننضّف المسافات اللي بتفضل وراه، عشان
    ما يبقاش عندنا print(" Socket.IO ...") بمسافة زايدة في الأول.
  * الملف ده بيتخطى نفسه.
"""

from __future__ import annotations

import os
import re
import sys

# ---------------------------------------------------------------------
# نطاقات الإيموجي
#
# مش بنستخدم مكتبة خارجية عن قصد - السكريبت ده لازم يشتغل على أي جهاز
# من غير pip install.
# ---------------------------------------------------------------------
EMOJI_RANGES = (
    "\U0001F000-\U0001FAFF"   # emoticons, pictographs, transport, symbols
    "☀-➿"           # misc symbols + dingbats: (tick) (cross) (warn) (recycle)
    "⬀-⯿"           # stars, extra arrows
    "←-⇿"           # arrows  <-- شوف الملحوظة تحت
    "︀-️"           # variation selectors
    "‍"                  # zero-width joiner
    "⃣"                  # keycap
    "™ℹ⤴⤵"
    "〰〽㊗㊙"
    "©®"            # (c) (r)
)

# الأسهم بتتشال بس لو جنبها إيموجي تاني أو لوحدها كأيقونة.
# لو عايزها تفضل زي ما هي، سيب ARROWS_ARE_EMOJI = False.
ARROWS_ARE_EMOJI = False

if not ARROWS_ARE_EMOJI:
    EMOJI_RANGES = EMOJI_RANGES.replace("←-⇿", "")

EMOJI_RE = re.compile("[" + EMOJI_RANGES + "]")

SENTINEL = "\x00"

# ---------------------------------------------------------------------
# إيه اللي بنعدّيه وإيه اللي بنتخطاه
# ---------------------------------------------------------------------
TEXT_EXTENSIONS = {
    ".py", ".pyw",
    ".md", ".txt", ".rst",
    ".html", ".htm", ".css", ".js", ".jsx", ".ts", ".tsx",
    ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg",
    ".ps1", ".bat", ".cmd", ".sh",
    ".csv",
}

EXTENSIONLESS_FILES = {"Dockerfile", "Makefile", ".gitignore", ".dockerignore"}

SKIP_DIRS = {
    ".git", "__pycache__", "dist", "build", "node_modules",
    ".venv", "venv", "env", ".mypy_cache", ".pytest_cache",
    ".nuitka-cache",
}

SELF_NAME = os.path.basename(os.path.abspath(__file__))


def is_text_file(path: str) -> bool:
    name = os.path.basename(path)
    if name == SELF_NAME:
        return False
    if name in EXTENSIONLESS_FILES:
        return True
    return os.path.splitext(name)[1].lower() in TEXT_EXTENSIONS


def clean_text(text: str) -> str:
    """
    بيشيل الإيموجي وبينضّف المسافة اللي بتفضل مكانه.

    الفكرة: بنحط علامة \\x00 مكان كل إيموجي الأول، وبعدين نتصرف في
    المسافات اللي حواليها حسب السياق، وبعدين نشيل العلامة. كده
    "print('(emoji) started')" بتطلع "print('started')" مش
    "print(' started')".
    """
    marked = EMOJI_RE.sub(SENTINEL, text)
    if SENTINEL not in marked:
        return text

    # علامات متتالية (زي إيموجي مركّب) بتبقى علامة واحدة
    marked = re.sub(SENTINEL + r"[ \t]*(?=" + SENTINEL + ")", "", marked)

    # علامة أول ما يفتح string أو قوس -> نشيل المسافة اللي بعدها
    marked = re.sub(r"(?<=[\"'(\[{])" + SENTINEL + r"[ \t]*", "", marked)

    # علامة قبل ما يقفل string أو قوس -> نشيل المسافة اللي قبلها
    marked = re.sub(r"[ \t]*" + SENTINEL + r"(?=[\"')\]}])", "", marked)

    # علامة في أول السطر (بعد المسافة البادئة) -> نحافظ على المسافة البادئة
    marked = re.sub(
        r"(?m)^([ \t]*)" + SENTINEL + r"[ \t]*",
        r"\1",
        marked,
    )

    # أي علامة فاضلة جوه النص -> بتتحول لمسافة واحدة
    marked = re.sub(r"[ \t]*" + SENTINEL + r"[ \t]*", " ", marked)

    # مسافات زايدة في آخر السطر
    marked = re.sub(r"(?m)[ \t]+$", "", marked)

    return marked


def iter_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            full = os.path.join(dirpath, filename)
            if is_text_file(full):
                yield full


def main() -> int:
    apply_changes = "--apply" in sys.argv
    root = os.path.dirname(os.path.abspath(__file__))

    changed_files = 0
    changed_lines = 0
    skipped: list[str] = []

    for path in iter_files(root):
        try:
            with open(path, "r", encoding="utf-8", newline="") as fh:
                original = fh.read()
        except (UnicodeDecodeError, OSError) as exc:
            skipped.append(f"{os.path.relpath(path, root)} ({type(exc).__name__})")
            continue

        if not EMOJI_RE.search(original):
            continue

        cleaned = clean_text(original)
        if cleaned == original:
            continue

        rel = os.path.relpath(path, root)
        print(f"\n--- {rel}")

        before = original.splitlines()
        after = cleaned.splitlines()
        for lineno, (old, new) in enumerate(zip(before, after), start=1):
            if old != new:
                changed_lines += 1
                print(f"  {lineno}:")
                print(f"    - {old.rstrip()}")
                print(f"    + {new.rstrip()}")

        changed_files += 1

        if apply_changes:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(cleaned)

    print("\n" + "=" * 60)
    if skipped:
        print("skipped (not valid utf-8):")
        for item in skipped:
            print("  " + item)
    print(f"files with emoji : {changed_files}")
    print(f"lines changed    : {changed_lines}")

    if apply_changes:
        print("\nDONE - files were rewritten. Review with: git diff")
    else:
        print("\nPREVIEW ONLY - nothing was written.")
        print("Run again with --apply to actually change the files.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
