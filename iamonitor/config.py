import json
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEFAULTS = {
    "host": "0.0.0.0",                         # 0.0.0.0 = acessível pelo celular na mesma rede; 127.0.0.1 = só o PC
    "port": 8765,                              # dashboard
    "access_token": None,                      # gerado automaticamente em data/token.txt
    "lmstudio_url": "http://localhost:1234",   # servidor real do LM Studio
    "proxy_port": 1235,                        # proxy contador de tokens -> LM Studio
    "projects": [],                            # pastas extras de projetos (git)
    "vscode_storage_dirs": [],                 # globalStorage extra (detectado automaticamente)
    "ntfy_topic": None,                        # tópico do ntfy.sh para notificações no celular
    "ntfy_server": "https://ntfy.sh",
    "alerts": {"gpu_temp_c": 83, "vram_percent": 95, "cpu_percent": 95, "ram_percent": 92},
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
    if not cfg["access_token"]:
        tf = DATA_DIR / "token.txt"
        if not tf.exists():
            tf.write_text(secrets.token_urlsafe(12))
        cfg["access_token"] = tf.read_text().strip()
    return cfg
