"""CPU / RAM / disk / network / GPU metrics."""
import shutil
import subprocess
import time

import psutil

_last_net = None
psutil.cpu_percent(None)  # prime


def _nvidia():
    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    q = "name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit,fan.speed,clocks.sm"
    try:
        out = subprocess.run([exe, f"--query-gpu={q}", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=4).stdout
    except Exception:
        return []

    def num(v):
        try:
            return float(v)
        except ValueError:
            return None

    gpus = []
    for i, line in enumerate(l for l in out.splitlines() if l.strip()):
        f = [x.strip() for x in line.split(",")]
        if len(f) < 9:
            continue
        gpus.append({"index": i, "name": f[0], "util": num(f[1]), "mem_used_mb": num(f[2]),
                     "mem_total_mb": num(f[3]), "temp_c": num(f[4]), "power_w": num(f[5]),
                     "power_limit_w": num(f[6]), "fan": num(f[7]), "clock_mhz": num(f[8])})
    # VRAM per process
    try:
        out = subprocess.run([exe, "--query-compute-apps=pid,process_name,used_memory",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=4).stdout
        procs = []
        for line in out.splitlines():
            f = [x.strip() for x in line.split(",")]
            if len(f) == 3:
                procs.append({"pid": f[0], "name": f[1].replace("\\", "/").split("/")[-1], "mem_mb": num(f[2])})
        if gpus:
            gpus[0]["processes"] = procs
    except Exception:
        pass
    return gpus


def _cpu_temp():
    try:
        t = psutil.sensors_temperatures()
        for key in ("coretemp", "k10temp", "cpu_thermal", "zenpower"):
            if key in t and t[key]:
                return t[key][0].current
    except Exception:
        pass
    return None


def snapshot():
    global _last_net
    vm = psutil.virtual_memory()
    net = psutil.net_io_counters()
    now = time.time()
    rate = {"down_kbs": 0, "up_kbs": 0}
    if _last_net:
        dt = max(now - _last_net[0], 1e-3)
        rate = {"down_kbs": (net.bytes_recv - _last_net[1]) / dt / 1024,
                "up_kbs": (net.bytes_sent - _last_net[2]) / dt / 1024}
    _last_net = (now, net.bytes_recv, net.bytes_sent)
    try:
        disk = psutil.disk_usage("/" if not psutil.WINDOWS else "C:\\")
        disk = {"used_gb": disk.used / 2**30, "total_gb": disk.total / 2**30, "percent": disk.percent}
    except Exception:
        disk = None
    return {
        "cpu": {"percent": psutil.cpu_percent(None), "per_core": psutil.cpu_percent(None, percpu=True),
                "cores": psutil.cpu_count(), "temp_c": _cpu_temp()},
        "ram": {"used_gb": vm.used / 2**30, "total_gb": vm.total / 2**30, "percent": vm.percent},
        "disk": disk,
        "net": rate,
        "gpus": _nvidia(),
        "ts": now,
    }
