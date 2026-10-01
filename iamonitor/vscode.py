"""VS Code + Zoo Code (Roo/Cline-family) activity and project health.

Zoo Code, like Roo Code, keeps every task under
<VS Code>/User/globalStorage/<extension-id>/tasks/<taskId>/ui_messages.json.
We scan every extension folder that has a `tasks/` dir, so it works regardless of the
exact extension id.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import psutil

_cache = {}


def _user_dirs():
    home = Path.home()
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", home / "AppData/Roaming"))
    elif sys.platform == "darwin":
        base = home / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    return [base / n / "User" for n in ("Code", "Code - Insiders", "VSCodium", "Cursor", "Windsurf")
            if (base / n / "User").exists()]


def _json_cached(path):
    try:
        m = path.stat().st_mtime
    except OSError:
        return None
    c = _cache.get(path)
    if c and c[0] == m:
        return c[1]
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        d = None
    _cache[path] = (m, d)
    return d


def _task_stats(tdir):
    msgs = _json_cached(tdir / "ui_messages.json") or []
    t = {"id": tdir.name, "tokens_in": 0, "tokens_out": 0, "cache_reads": 0, "cost": 0.0,
         "requests": 0, "title": None, "last_ts": None, "last_say": None}
    for m in msgs:
        if not isinstance(m, dict):
            continue
        if m.get("say") == "api_req_started" and m.get("text"):
            try:
                j = json.loads(m["text"])
                t["tokens_in"] += j.get("tokensIn") or 0
                t["tokens_out"] += j.get("tokensOut") or 0
                t["cache_reads"] += j.get("cacheReads") or 0
                t["cost"] += j.get("cost") or 0
                t["requests"] += 1
            except Exception:
                pass
        if t["title"] is None and m.get("say") in ("text", "user_feedback") and m.get("text"):
            t["title"] = m["text"].strip().replace("\n", " ")[:120]
        t["last_ts"] = m.get("ts") or t["last_ts"]
        t["last_say"] = m.get("say") or m.get("ask") or t["last_say"]
    return t


def agent_activity(extra_dirs=()):
    exts = []
    for u in _user_dirs():
        gs = u / "globalStorage"
        if gs.exists():
            exts += [d for d in gs.iterdir() if (d / "tasks").is_dir()]
    exts += [Path(d) for d in extra_dirs if (Path(d) / "tasks").is_dir()]
    res = []
    now = time.time()
    for ext in exts:
        tasks = []
        tdirs = [d for d in (ext / "tasks").iterdir() if (d / "ui_messages.json").exists()]
        tdirs.sort(key=lambda d: (d / "ui_messages.json").stat().st_mtime, reverse=True)
        for d in tdirs[:100]:
            tasks.append(_task_stats(d))
        tot = {k: sum(t[k] for t in tasks) for k in ("tokens_in", "tokens_out", "cache_reads", "cost", "requests")}
        active = bool(tdirs) and now - (tdirs[0] / "ui_messages.json").stat().st_mtime < 60
        res.append({"extension": ext.name, "task_count": len(tdirs), "totals": tot,
                    "active": active, "tasks": tasks[:8]})
    return res


def vscode_running():
    n = 0
    for p in psutil.process_iter(["name"]):
        try:
            if (p.info["name"] or "").lower().split(".")[0] in ("code", "code - insiders", "codium", "cursor"):
                n += 1
        except Exception:
            pass
    return n > 0


def recent_workspaces(limit=5):
    out = []
    for u in _user_dirs():
        ws = u / "workspaceStorage"
        if not ws.exists():
            continue
        for d in ws.iterdir():
            f = d / "workspace.json"
            if f.exists():
                j = _json_cached(f) or {}
                uri = j.get("folder")
                if uri and uri.startswith("file://"):
                    p = unquote(urlparse(uri).path)
                    if sys.platform == "win32":
                        p = p.lstrip("/")
                    if os.path.isdir(p):
                        out.append((f.stat().st_mtime, p))
    out.sort(reverse=True)
    seen, res = set(), []
    for _, p in out:
        if p not in seen:
            seen.add(p)
            res.append(p)
    return res[:limit]


def _git(path, *args):
    return subprocess.run(["git", "-C", path, *args], capture_output=True, text=True, timeout=8).stdout.strip()


def project_health(path):
    info = {"path": path, "name": os.path.basename(path.rstrip("/\\")), "git": False}
    try:
        if _git(path, "rev-parse", "--is-inside-work-tree") != "true":
            return info
        info["git"] = True
        info["branch"] = _git(path, "rev-parse", "--abbrev-ref", "HEAD")
        status = _git(path, "status", "--porcelain").splitlines()
        info["changed_files"] = len(status)
        info["untracked"] = sum(1 for s in status if s.startswith("??"))
        info["last_commit"] = _git(path, "log", "-1", "--format=%h %s (%cr)")
        info["commits_today"] = len(_git(path, "log", "--since=midnight", "--format=%h").splitlines())
        ab = _git(path, "rev-list", "--left-right", "--count", "@{u}...HEAD").split()
        if len(ab) == 2:
            info["behind"], info["ahead"] = int(ab[0]), int(ab[1])
        info["stash"] = len(_git(path, "stash", "list").splitlines())
    except Exception as e:
        info["error"] = str(e)
    return info


def projects(cfg):
    paths = list(dict.fromkeys([*cfg.get("projects", []), *recent_workspaces()]))
    return [project_health(p) for p in paths if os.path.isdir(p)]
