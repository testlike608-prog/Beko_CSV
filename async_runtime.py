"""
async_runtime.py
----------------
event loop واحد لعملية خط الإنتاج كلها — بديل الثريدات الكتير.

قبل كده كل تريجر كان بيفتح ثريد جديد (writer لكل محطة، auto_load،
listener لكل سكانر، watchdog لكل client ...) وكلهم بيكلموا نفس السوكيت
في نفس الوقت. دلوقتي كل ده بقى tasks على loop واحد:

    - مفيش تنافس على السوكيت: كل client عنده asyncio.Lock للطلب/الرد.
    - الإيقاف نظيف: بنعمل cancel للـ tasks بدل ما نستنى ثريدات واقفة.
    - الانتظار (sleep / انتظار رد / انتظار الـ queue) مبياكلش CPU.

الـ loop بيشتغل في ثريد خلفي واحد بس عشان يفضل مستقل عن سيرفر الويب
(FastAPI أو Flask) — لو أي حاجة في العملية اتأخرت، الواجهة مبتتأثرش.

أي كود بلوكنج حقيقي (pyodbc، VisionMaster .NET، pandas) بيتنفذ بـ
asyncio.to_thread عشان ما يوقفش الـ loop.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Awaitable, Callable, Optional

_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_start_lock = threading.Lock()


def get_loop() -> asyncio.AbstractEventLoop:
    """الـ loop بتاع العملية — بيتعمل أول مرة بس ويفضل شغال لحد ما البرنامج يقفل."""
    global _loop, _loop_thread
    with _start_lock:
        if _loop is None:
            ready = threading.Event()
            loop = asyncio.new_event_loop()

            def _run():
                asyncio.set_event_loop(loop)
                loop.call_soon(ready.set)
                loop.run_forever()

            _loop_thread = threading.Thread(target=_run, name="beko-async-loop", daemon=True)
            _loop_thread.start()
            ready.wait()
            _loop = loop
    return _loop


def in_loop_thread() -> bool:
    return _loop_thread is not None and threading.current_thread() is _loop_thread


def submit(coro: Awaitable[Any]):
    """تشغيل coroutine على loop العملية من أي ثريد. بيرجع concurrent.futures.Future."""
    return asyncio.run_coroutine_threadsafe(coro, get_loop())


def run(coro: Awaitable[Any], timeout: Optional[float] = None) -> Any:
    """تشغيل coroutine ومستني النتيجة — ممنوع من جوه الـ loop نفسه (هيعمل deadlock)."""
    if in_loop_thread():
        raise RuntimeError("async_runtime.run() cannot be called from the process loop")
    return submit(coro).result(timeout)


def call_soon(fn: Callable[..., Any], *args: Any) -> None:
    """تنفيذ دالة عادية جوه الـ loop — آمنة من أي ثريد."""
    if in_loop_thread():
        fn(*args)
    else:
        get_loop().call_soon_threadsafe(fn, *args)


class AsyncQueue:
    """
    asyncio.Queue عايش على loop العملية، بس put() آمنة من أي ثريد.

    الـ queues اليدوية (queue_manual_FOR_FAILURE ...) بيكتب فيها سيرفر
    الويب من ثريد تاني، والعملية بتقرا منها بـ await. نفس واجهة
    queue.Queue اللي الراوترات بتستخدمها (put / qsize) فمفيش راوتر اتغيّر.
    """

    def __init__(self):
        self._q: asyncio.Queue = asyncio.Queue()

    # ---- من أي ثريد ----
    def put(self, item=None, block=True, timeout=None, *, value=None):  # noqa: ARG002
        if item is None and value is not None:
            item = value
        call_soon(self._q.put_nowait, item)

    def put_nowait(self, item):
        call_soon(self._q.put_nowait, item)

    def qsize(self) -> int:
        return self._q.qsize()

    def empty(self) -> bool:
        return self._q.empty()

    # ---- من جوه الـ loop بس ----
    async def get(self):
        return await self._q.get()

    def get_nowait(self):
        return self._q.get_nowait()

    def task_done(self):
        self._q.task_done()

    def clear(self):
        """تفريغ الـ queue — لازم تتنادى من جوه الـ loop."""
        q = self._q
        while not q.empty():
            try:
                q.get_nowait()
                q.task_done()
            except (asyncio.QueueEmpty, ValueError):
                break
