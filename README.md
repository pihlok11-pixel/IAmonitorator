# IAmonitorator

Dashboard local (http://localhost:8765) para acompanhar sua máquina, o LM Studio e o Zoo Code no VS Code.

## Uso
```
pip install -r requirements.txt
python run.py
```
(Windows: `py run.py`). O navegador abre sozinho.

## O que mostra
- **CPU / RAM / disco / rede** (psutil) e **GPU NVIDIA** (via `nvidia-smi`: uso, VRAM, temperatura, potência, processos).
- **LM Studio**: servidor online/offline, modelos carregados (quantização, contexto), RAM do app.
- **Tokens**: total acumulado (persistido em `data/tokens.json`), da sessão, último minuto, tok/s e TTFT por requisição.
- **VS Code / Zoo Code**: lê `globalStorage/<extensão>/tasks/*/ui_messages.json` (tarefas, chamadas, tokens, custo, "trabalhando agora"). Detecta qualquer extensão estilo Roo/Cline automaticamente.
- **Projetos**: branch, arquivos alterados, ahead/behind, commits de hoje, último commit — dos workspaces recentes do VS Code + `projects` do config.

## Contar tokens do LM Studio
O LM Studio não expõe um contador global de tokens, então o app roda um **proxy transparente** em `http://localhost:1235/v1` → `:1234`.
No Zoo Code (provedor "LM Studio" ou "OpenAI Compatible") troque a Base URL para `http://localhost:1235/v1`. Streaming funciona; se a resposta não trouxer `usage`, o valor é estimado (marcado com `~`).

## Configuração (opcional)
Copie `config.example.json` para `config.json` (porta, URL do LM Studio, `projects`, `vscode_storage_dirs`).

## Limitações
Leitura de GPU só via `nvidia-smi` (sua RTX 2080 Ti funciona). Temperatura de CPU só em Linux.

## Ver no celular
1. Rode `python run.py` no PC. O terminal mostra um **link com token** e um **QR code** (`Celular: http://192.168.x.x:8765/?token=...`).
2. No celular (mesmo Wi-Fi), escaneie o QR / abra o link. O token fica salvo no navegador.
3. Instale como app: **Android (Chrome)** menu ⋮ → *Instalar app*; **iPhone (Safari)** Compartilhar → *Adicionar à Tela de Início*.
4. Se o Windows perguntar, permita o Python no firewall para **redes privadas**.

O token está em `data/token.txt` (ou defina `access_token` no config). Quem não tem o token recebe 401. Para acesso só no PC use `"host": "127.0.0.1"`.

### Fora de casa (4G/5G)
Instale o [Tailscale](https://tailscale.com) (grátis) no PC e no celular e abra `http://<ip-tailscale-do-pc>:8765/?token=...`. Não exponha a porta 8765 na internet.

## Notificações no celular (ntfy)
1. Instale o app **ntfy** (Android/iOS) e assine um tópico secreto, ex.: `iamonitor-fulano-8231`.
2. No `config.json`: `{"ntfy_topic": "iamonitor-fulano-8231"}`.
3. Você recebe alertas de: GPU ≥ 83 °C, VRAM ≥ 95 %, CPU/RAM no limite, LM Studio que caiu e Zoo Code que terminou/parou uma tarefa. Limites ajustáveis em `alerts`.
