"""
station_logs.py
---------------
مخزن اللوجز الخاص بكل محطة — بيعرضه مربّع الـ logs اللي تحت كل كارت في الـ Home.

كل سطر بياخد رقم تسلسلي (seq) واحد على مستوى البرنامج كله، فالواجهة بتسأل
"هاتلي اللي بعد آخر seq شفته" — مفيش سطر بيضيع ولا بيتكرر حتى لو الصفحة
اتعمل لها refresh أو السيرفر فضل شغال ساعات.

التيرمنال مش بيتأثر بالملف ده خالص — كل واحد بيفضل يعمل print زي ما هو.
"""

from __future__ import annotations

import threading
import time
from collections import deque

MAX_LINES = 1000  # لكل محطة — الأقدم بيتشال لوحده

_lock = threading.Lock()
_seq = 0
_buffers: dict[int, deque] = {1: deque(maxlen=MAX_LINES), 2: deque(maxlen=MAX_LINES)}


def add(station: int, source: str, level: str, msg: str) -> None:
    """إضافة سطر للوج المحطة. أي station غير 1 أو 2 بيتجاهل."""
    global _seq
    buf = _buffers.get(station)
    if buf is None:
        return
    with _lock:
        _seq += 1
        buf.append(
            {
                "seq": _seq,
                "ts": time.time(),
                "src": source or "",
                "level": str(level or "INFO").upper(),
                "msg": str(msg),
            }
        )


def since(station: int, after: int = 0, limit: int = 300) -> dict:
    """
    السطور اللي بعد `after`. أول تحميل للصفحة (after=0) بيرجع آخر `limit` سطر.
    `last` هو آخر seq موجود — الواجهة بتبعته في الطلب الجاي.
    """
    buf = _buffers.get(station)
    if buf is None:
        return {"lines": [], "last": after}
    with _lock:
        lines = [e for e in buf if e["seq"] > after]
        last = _seq
    if len(lines) > limit:
        lines = lines[-limit:]
    return {"lines": lines, "last": last}
