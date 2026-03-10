# JARVIS

JARVIS (Just A Rather Very Intelligent System) is a modular local-first AI assistant platform designed to run as a persistent operating layer on a user's computer.

This repository provides:

- An async runtime with lifecycle management, observability, and a message bus
- Multi-agent planning and execution
- Local-first intelligence providers with heuristic and Ollama-compatible backends
- Tool-planned autonomous execution for workspace and system requests
- Persistent memory with SQLite and a local semantic index
- A personal knowledge graph and adaptive learning loop
- Durable automation jobs that restore after runtime restart
- Background command queue with async submission and cancellation
- Windows startup registration controls for boot persistence
- Desktop automation primitives for mouse and keyboard control
- Voice, vision, web, automation, and system-control service abstractions
- A FastAPI developer surface, realtime event streams, a browser dashboard, and an optional PyQt dashboard
- A plugin SDK with auto-loading example plugins

## Quick Start

1. Create a virtual environment.
2. Install the core dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Start the API-backed runtime:

```powershell
python -m jarvis.main --api
```

Then open `http://127.0.0.1:8000/dashboard`.

4. Submit a command:

```powershell
curl -X POST http://127.0.0.1:8000/command -H "Content-Type: application/json" -d "{\"text\":\"Jarvis remember that my favorite editor is VS Code\"}"
```

## Optional Multimodal Features

Install `requirements-optional.txt` to enable heavier voice, vision, UI, and desktop integrations such as Porcupine, Whisper, OpenCV, PyQt, and PyAutoGUI.

## Run Without API Dependencies

The core runtime can execute one-shot commands without FastAPI or Uvicorn:

```powershell
python -m jarvis.main --once "Jarvis remember that my favorite editor is VS Code"
python -m jarvis.main --once "What did I say about editor"
python -m jarvis.main --startup-status
```

## Validation

```powershell
python -m unittest discover -s tests -v
```

## Realtime Ops

- Browser dashboard: `/dashboard`
- Server-sent event stream: `/stream/events`
- WebSocket event stream: `/ws/events`
- Async command submission: `POST /command/async`
- Async command inspection: `GET /commands`, `GET /commands/{request_id}`
- Async command cancellation: `POST /commands/{request_id}/cancel`
- Confirmation review: `GET /confirmations`, `POST /confirmations/{confirmation_id}/approve`, `POST /confirmations/{confirmation_id}/reject`
- Startup controls: `GET /startup`, `POST /startup/install`, `POST /startup/uninstall`
- Job inspection: `GET /jobs`
- Job cancellation: `POST /jobs/{job_id}/cancel`

## Architecture

The runtime is organized under `jarvis/`:

- `core`: configuration, lifecycle, event bus, logging, shared models
- `brain`: task planning and reasoning loops
- `agents`: specialist agents coordinated by the commander
- `memory`: long-term storage and semantic recall
- `brain/intelligence.py`: local-first reasoning providers and summarization
- `agents/autonomous.py`: tool-driven fallback agent for generic workspace/system tasks
- `brain/learning.py`: adaptive behavior tracking and insights
- `voice`: wake word, VAD, STT, TTS, and orchestration
- `vision`: OCR and visual context extraction
- `system_control`: safe OS and shell integration
- `system_control/desktop.py`: optional mouse and keyboard automation backend
- `system_control/startup.py`: Windows scheduled-task startup persistence
- `automation`: scheduled jobs and background workflows
- `web_intelligence`: research, news, weather, and search providers
- `plugins`: plugin SDK and auto-loadable integrations
- `api`: FastAPI routes for developer access
- `ui`: optional PyQt dashboard

## Safety Model

JARVIS uses:

- a command risk assessor
- plan-level confirmation checks for sensitive steps
- tool-level confirmation enforcement for dangerous tools
- configurable confirmation gates for dangerous actions
- sandbox-aware shell execution
- voice identity verification hooks
- permission categories for tools and agents

## Startup Management

JARVIS can inspect or register a Windows logon task for persistent startup:

```powershell
python -m jarvis.main --startup-status
python -m jarvis.main --install-startup --startup-mode api
python -m jarvis.main --uninstall-startup
```

Natural-language startup changes such as `Jarvis enable startup in background mode` are routed through the normal confirmation flow before execution.

Desktop automation is also available behind confirmation:

```powershell
python -m jarvis.main --once "Jarvis show desktop status"
python -m jarvis.main --once "Jarvis click at 100 200"
python -m jarvis.main --once "Jarvis press ctrl+shift+s"
```

## Persistence

By default JARVIS stores runtime data under `.jarvis_runtime/` in the project root:

- `jarvis.db`: structured memory and task history
- `semantic_memory.json`: semantic index for recall
- `jarvis.log`: runtime logs

## Next Steps

- Configure API keys or external providers in `jarvis/config/settings.yaml`
- Extend `jarvis/plugins/base.py` and `jarvis/plugins/sdk.py` to add new capabilities
- Replace fallback providers with GPU-backed local or cloud models
