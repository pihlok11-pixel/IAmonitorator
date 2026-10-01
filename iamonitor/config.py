import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEFAULTS = {
    "port": 8765,                              # dashboard
    "lmstudio_url": "http://localhost:1234",   # real LM Studio server
    "proxy_port": 1235,                        # token-counting proxy -> LM Studio
    "projects": [],                            # extra project folders to inspect (git)
    "vscode_storage_dirs": [],                 # extra globalStorage dirs (auto-detected otherwise)
}


def load():
    cfg = dict(DEFAULTS)
    p = ROOT / "config.json"
    if p.exists():
        try:
            cfg.update(json.loads(p.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[config] config.json inválido, usando padrões: {e}")
    DATA_DIR.mkdir(exist_ok=True)
    return cfg
