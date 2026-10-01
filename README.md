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
GPU AMD/Intel não é lida (só NVIDIA). Temperatura de CPU só em Linux.
