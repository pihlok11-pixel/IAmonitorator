"""Transparent proxy in front of LM Studio that counts tokens.

Point Zoo Code / Roo / Continue / any OpenAI-compatible client at
http://localhost:<proxy_port>/v1 instead of :1234. Everything is forwarded as-is
(streaming included); the `usage` block of the response is recorded.
"""
import http.client
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import tokens

HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailers", "upgrade", "proxy-authorization"}


def make_handler(target):
    t = urlparse(target)
    host, port = t.hostname, t.port or 80

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _forward(self):
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            counted = self.command == "POST" and any(
                p in self.path for p in ("/chat/completions", "/completions", "/embeddings", "/responses"))
            model, est_prompt = None, 0
            if counted:
                try:
                    j = json.loads(body)
                    model = j.get("model")
                    est_prompt = len(json.dumps(j.get("messages") or j.get("prompt") or j.get("input") or "")) // 4
                except Exception:
                    pass
                tokens.begin()
            start = time.time()
            usage, ttft, out_chars, finished = None, None, 0, False
            try:
                c = http.client.HTTPConnection(host, port, timeout=900)
                hdrs = {k: v for k, v in self.headers.items() if k.lower() not in HOP | {"host", "content-length"}}
                hdrs["Content-Length"] = str(len(body))
                c.request(self.command, self.path, body=body, headers=hdrs)
                r = c.getresponse()
                self.send_response(r.status)
                is_sse = "text/event-stream" in (r.getheader("Content-Type") or "")
                for k, v in r.getheaders():
                    if k.lower() not in HOP | {"content-length"}:
                        self.send_header(k, v)
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                buf, whole = b"", []
                while True:
                    chunk = r.read1(8192) if hasattr(r, "read1") else r.read(8192)
                    if not chunk:
                        break
                    if ttft is None and counted:
                        ttft = time.time() - start
                    self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                    self.wfile.flush()
                    if counted:
                        if is_sse:
                            buf += chunk
                            *lines, buf = buf.split(b"\n")
                            for ln in lines:
                                u, n = _parse_sse(ln)
                                usage = u or usage
                                out_chars += n
                        else:
                            whole.append(chunk)
                self.wfile.write(b"0\r\n\r\n")
                finished = True
                if counted and not is_sse:
                    try:
                        j = json.loads(b"".join(whole))
                        usage = j.get("usage")
                        out_chars = len(json.dumps(j.get("choices", "")))
                    except Exception:
                        pass
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                if not finished:
                    try:
                        self.send_error(502, f"LM Studio inacessível: {e}")
                    except Exception:
                        pass
            finally:
                if counted:
                    est = not usage
                    p = (usage or {}).get("prompt_tokens", est_prompt) or 0
                    cmp_ = (usage or {}).get("completion_tokens", out_chars // 4) or 0
                    tokens.end(model, p, cmp_, time.time() - start, ttft, est)

        do_GET = do_POST = do_PUT = do_DELETE = do_OPTIONS = _forward

    return H


def _parse_sse(line):
    line = line.strip()
    if not line.startswith(b"data:") or line.endswith(b"[DONE]"):
        return None, 0
    try:
        j = json.loads(line[5:])
    except Exception:
        return None, 0
    n = 0
    for ch in j.get("choices", []) or []:
        d = ch.get("delta") or {}
        n += len(d.get("content") or "") + len(d.get("reasoning_content") or "")
    return j.get("usage"), n


def start(cfg):
    srv = ThreadingHTTPServer(("127.0.0.1", cfg["proxy_port"]), make_handler(cfg["lmstudio_url"]))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
