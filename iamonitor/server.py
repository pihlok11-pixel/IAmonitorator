import json
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config, lmstudio, proxy, system, tokens, vscode

STATIC = Path(__file__).parent / "static"
_slow = {"ts": 0, "data": None}
_lock = threading.Lock()


def _slow_data(cfg):
    """Git/VS Code scans are heavier: refresh at most every 10 s."""
    with _lock:
        if time.time() - _slow["ts"] > 10:
            _slow["data"] = {"vscode_running": vscode.vscode_running(),
                             "agents": vscode.agent_activity(cfg["vscode_storage_dirs"]),
                             "projects": vscode.projects(cfg)}
            _slow["ts"] = time.time()
        return _slow["data"]


def collect(cfg):
    return {"system": system.snapshot(),
            "lmstudio": lmstudio.snapshot(cfg["lmstudio_url"]),
            "tokens": tokens.snapshot(),
            "dev": _slow_data(cfg),
            "proxy_url": f"http://localhost:{cfg['proxy_port']}/v1"}


def main():
    cfg = config.load()
    proxy.start(cfg)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path.startswith("/api/all"):
                body, ctype = json.dumps(collect(cfg), default=str).encode(), "application/json"
            elif self.path in ("/", "/index.html"):
                body, ctype = (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("127.0.0.1", cfg["port"]), H)
    url = f"http://localhost:{cfg['port']}"
    print(f"IAmonitorator rodando em {url}")
    print(f"Proxy de tokens: http://localhost:{cfg['proxy_port']}/v1  ->  {cfg['lmstudio_url']}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
