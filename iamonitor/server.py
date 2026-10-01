import hmac
import json
import socket
import threading
import time
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import alerts, config, lmstudio, proxy, system, tokens, vscode

STATIC = Path(__file__).parent / "static"
TYPES = {".html": "text/html; charset=utf-8", ".json": "application/json", ".js": "text/javascript",
         ".svg": "image/svg+xml", ".webmanifest": "application/manifest+json"}
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
            "proxy_url": f"http://localhost:{cfg['proxy_port']}/v1",
            "host": socket.gethostname()}


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    cfg = config.load()
    proxy.start(cfg)
    alerts.start(cfg, collect)
    token = cfg["access_token"]

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _authed(self, q):
            if self.client_address[0] in ("127.0.0.1", "::1"):
                return True
            ck = SimpleCookie(self.headers.get("Cookie", ""))
            given = (q.get("token") or [None])[0] or (ck["iam_token"].value if "iam_token" in ck else "")
            return hmac.compare_digest(given or "", token)

        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if not self._authed(q):
                self.send_response(401)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write("Acesso negado. Abra o link com ?token=... mostrado no terminal do PC.".encode())
                return
            if u.path.startswith("/api/all"):
                body, ctype = json.dumps(collect(cfg), default=str).encode(), "application/json"
            else:
                name = "index.html" if u.path == "/" else u.path.lstrip("/")
                f = (STATIC / name).resolve()
                if STATIC.resolve() not in f.parents or not f.is_file():
                    self.send_error(404)
                    return
                body, ctype = f.read_bytes(), TYPES.get(f.suffix, "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if q.get("token"):  # remember on the phone so the PWA needs no token in the URL
                self.send_header("Set-Cookie", f"iam_token={q['token'][0]}; Max-Age=31536000; Path=/; SameSite=Lax")
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer((cfg["host"], cfg["port"]), H)
    local = f"http://localhost:{cfg['port']}"
    lan = f"http://{lan_ip()}:{cfg['port']}/?token={token}"
    print(f"\nIAmonitorator\n  PC:      {local}\n  Celular: {lan}  (mesmo Wi-Fi)")
    print(f"  Proxy de tokens: http://localhost:{cfg['proxy_port']}/v1 -> {cfg['lmstudio_url']}")
    if cfg.get("ntfy_topic"):
        print(f"  Notificações: ntfy '{cfg['ntfy_topic']}'")
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(lan)
        qr.print_ascii(invert=True)
    except ImportError:
        print("  (pip install qrcode para exibir QR code aqui)")
    try:
        webbrowser.open(local)
    except Exception:
        pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
