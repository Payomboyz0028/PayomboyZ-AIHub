"""Hub worker health, bounded jobs, and cooperative restart (no network probes)."""
import asyncio
import functools
import json
import os
import threading
import time
import uuid
from pathlib import Path

_lock = threading.Lock()
_jobs = {}
_draining = threading.Event()
_last_job_end = time.monotonic()


def status_directory():
    value = os.environ.get("HUB_SUPERVISOR_DIR")
    return Path(value) if value else None


def atomic_json(path, data):
    path = Path(path)
    temporary = path.with_suffix(f".{threading.get_ident()}.tmp")
    temporary.write_text(json.dumps(data), encoding="utf-8")
    for attempt in range(4):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 3:
                raise
            # Windows readers/antivirus may briefly deny file replacement.
            time.sleep(.05)


def request_recycle(reason):
    directory = status_directory()
    if directory:
        _draining.set()
        atomic_json(directory / "restart.json", {"reason": reason, "pid": os.getpid()})


def is_draining():
    directory = status_directory()
    if directory and (directory / "drain.json").exists():
        _draining.set()
    return _draining.is_set()


def job_snapshot():
    now = time.monotonic()
    with _lock:
        return {
            "active_jobs": len(_jobs),
            "oldest_job_seconds": max((now - start for start in _jobs.values()), default=0),
            "idle_seconds": now - _last_job_end,
        }


def managed_job(timeout=None):
    """Bound total await time; a stuck executor thread requires process recycling."""
    def decorate(function):
        @functools.wraps(function)
        async def guarded(*args, **kwargs):
            global _last_job_end
            if is_draining():
                raise RuntimeError("ระบบกำลังรีสตาร์ตเพื่อบำรุงรักษา กรุณาลองอีกครั้งในอีกสักครู่")
            limit = timeout if timeout is not None else float(os.environ.get("HUB_JOB_TIMEOUT_SECONDS", "600"))
            job_id = uuid.uuid4().hex
            with _lock:
                if len(_jobs) >= int(os.environ.get("HUB_MAX_ACTIVE_JOBS", "4")):
                    raise RuntimeError("งาน AI กำลังเต็ม กรุณาลองใหม่อีกสักครู่")
                _jobs[job_id] = time.monotonic()
            try:
                # asyncio.wait provides a hard caller deadline even when an
                # underlying coroutine suppresses cancellation.
                task = asyncio.create_task(function(*args, **kwargs))
                try:
                    done, _ = await asyncio.wait({task}, timeout=limit)
                    if not done:
                        request_recycle("job-timeout")
                        raise TimeoutError(f"งานใช้เวลาเกิน {limit:g} วินาที ระบบกำลังกู้คืน กรุณาส่งคำขอใหม่")
                    return task.result()
                finally:
                    if not task.done():
                        task.cancel()
                        task.add_done_callback(_consume_task_result)
            finally:
                with _lock:
                    _jobs.pop(job_id, None)
                    _last_job_end = time.monotonic()
        return guarded
    return decorate


def _consume_task_result(task):
    if not task.cancelled():
        task.exception()


async def monitor_bot(client, component):
    """Heartbeat runs ON the Discord event loop, so a frozen loop cannot fake health."""
    directory = status_directory()
    if not directory:
        return
    while not client.is_closed():
        state = job_snapshot()
        try:
            atomic_json(directory / f"{component}.json", {
                "pid": os.getpid(), "tick": time.monotonic(),
                "ready": client.is_ready(), "component": component, **state,
            })
        except OSError as exc:
            print(f"[HUB] {component}: heartbeat write failed ({type(exc).__name__})", flush=True)
        if is_draining() and state["active_jobs"] == 0 and state["idle_seconds"] >= 15:
            print(f"[HUB] {component}: jobs drained; closing Discord connection", flush=True)
            await client.close()
            return
        await asyncio.sleep(5)


def install_bot_monitor(client, component):
    """Register before run(), including login/reconnect periods before on_ready."""
    original = client.setup_hook

    async def setup_hook():
        await original()
        if status_directory():
            client._hub_health_task = asyncio.create_task(monitor_bot(client, component))

    client.setup_hook = setup_hook
