"""Push notifications to the phone through ntfy.sh (free; install the ntfy app and subscribe to your topic)."""
import threading
import time
import urllib.request

_last = {}
_state = {}


def notify(cfg, key, title, msg, priority="default", cooldown=600):
    if not cfg.get("ntfy_topic") or time.time() - _last.get(key, 0) < cooldown:
        return
    _last[key] = time.time()
    req = urllib.request.Request(f"{cfg['ntfy_server']}/{cfg['ntfy_topic']}", data=msg.encode("utf-8"),
                                 headers={"Title": title.encode("utf-8"), "Priority": priority})
    try:
        urllib.request.urlopen(req, timeout=8).read()
    except Exception as e:
        print(f"[ntfy] falhou: {e}")


def check(cfg, d):
    a, s = cfg["alerts"], d["system"]
    g = s["gpus"][0] if s["gpus"] else None
    if g:
        if g["temp_c"] and g["temp_c"] >= a["gpu_temp_c"]:
            notify(cfg, "gputemp", "🔥 GPU quente", f"{g['name']} em {g['temp_c']:.0f} °C", "high")
        if g["mem_total_mb"] and g["mem_used_mb"] / g["mem_total_mb"] * 100 >= a["vram_percent"]:
            notify(cfg, "vram", "⚠️ VRAM quase cheia", f"{g['mem_used_mb']:.0f}/{g['mem_total_mb']:.0f} MB", "high")
    if s["cpu"]["percent"] >= a["cpu_percent"]:
        notify(cfg, "cpu", "CPU no limite", f"{s['cpu']['percent']:.0f}%")
    if s["ram"]["percent"] >= a["ram_percent"]:
        notify(cfg, "ram", "RAM quase cheia", f"{s['ram']['percent']:.0f}%")
    online = d["lmstudio"]["online"]
    if _state.get("lm") is True and not online:
        notify(cfg, "lm_off", "LM Studio caiu", "Servidor local ficou offline", "high", 60)
    _state["lm"] = online
    for ag in d["dev"]["agents"]:
        k = "agent:" + ag["extension"]
        if _state.get(k) and not ag["active"]:
            t = ag["tasks"][0] if ag["tasks"] else {}
            notify(cfg, k, "✅ Zoo Code terminou/parou", (t.get("title") or "tarefa")[:100], "default", 120)
        _state[k] = ag["active"]


def start(cfg, collect):
    def loop():
        while True:
            try:
                check(cfg, collect(cfg))
            except Exception as e:
                print(f"[alerts] {e}")
            time.sleep(5)
    threading.Thread(target=loop, daemon=True).start()
