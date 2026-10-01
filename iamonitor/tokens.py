"""Persistent token accounting fed by the LM Studio proxy."""
import json
import threading
import time
from collections import deque

from .config import DATA_DIR

_FILE = DATA_DIR / "tokens.json"
_lock = threading.Lock()
_recent = deque(maxlen=200)
_total = {"prompt": 0, "completion": 0, "requests": 0, "since": time.time()}
_session = {"prompt": 0, "completion": 0, "requests": 0, "since": time.time()}
_active = 0

try:
    _total.update(json.loads(_FILE.read_text()))
except Exception:
    pass


def _save():
    try:
        _FILE.write_text(json.dumps(_total))
    except Exception:
        pass


def begin():
    global _active
    with _lock:
        _active += 1


def end(model, prompt, completion, duration, ttft, estimated):
    global _active
    with _lock:
        _active = max(0, _active - 1)
        for d in (_total, _session):
            d["prompt"] += prompt
            d["completion"] += completion
            d["requests"] += 1
        gen_time = max(duration - (ttft or 0), 1e-3)
        _recent.appendleft({"ts": time.time(), "model": model, "prompt": prompt, "completion": completion,
                            "duration": duration, "ttft": ttft, "tps": completion / gen_time,
                            "estimated": estimated})
        _save()


def snapshot():
    now = time.time()
    with _lock:
        last60 = [r for r in _recent if now - r["ts"] <= 60]
        return {
            "total": dict(_total), "session": dict(_session), "active_requests": _active,
            "tokens_last_min": sum(r["prompt"] + r["completion"] for r in last60),
            "recent": list(_recent)[:15],
            "avg_tps": (sum(r["tps"] for r in last60) / len(last60)) if last60 else None,
        }
