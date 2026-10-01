"""Query LM Studio's local server for loaded models and status."""
import json
import shutil
import subprocess
import urllib.request

import psutil


def _get(url, timeout=2):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def snapshot(base):
    out = {"online": False, "models": [], "loaded": [], "process": None}
    for p in psutil.process_iter(["name", "memory_info", "cpu_percent"]):
        try:
            if "lm studio" in (p.info["name"] or "").lower() or "lm-studio" in (p.info["name"] or "").lower():
                mi = p.info["memory_info"]
                out["process"] = out["process"] or {"ram_mb": 0}
                out["process"]["ram_mb"] += (mi.rss if mi else 0) / 2**20
        except Exception:
            pass
    models = None
    try:  # richer beta REST API: state, context length, quantization
        models = _get(base + "/api/v0/models").get("data", [])
        out["online"] = True
    except Exception:
        try:
            models = [{"id": m["id"]} for m in _get(base + "/v1/models").get("data", [])]
            out["online"] = True
        except Exception as e:
            out["error"] = str(e)
    for m in models or []:
        item = {"id": m.get("id"), "state": m.get("state"), "type": m.get("type"),
                "quant": m.get("quantization"), "arch": m.get("arch"),
                "max_ctx": m.get("max_context_length"), "loaded_ctx": m.get("loaded_context_length")}
        out["models"].append(item)
        if item["state"] == "loaded" or (item["state"] is None and out["online"]):
            out["loaded"].append(item)
    return out


def lms_ps():
    """Extra detail from the `lms` CLI (model size, context, TTL), if installed."""
    exe = shutil.which("lms")
    if not exe:
        return None
    try:
        return subprocess.run([exe, "ps"], capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return None
