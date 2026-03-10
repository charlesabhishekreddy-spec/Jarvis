# JARVIS

JARVIS (Just A Rather Very Intelligent System) is a modular local-first AI assistant platform designed to run as a persistent operating layer on a user's computer.

This repository provides:

- An async runtime with lifecycle management, observability, and a message bus
- Multi-agent planning and execution
- Local-first intelligence providers with heuristic and Ollama-compatible backends
- Persistent memory with SQLite and a local semantic index
- A personal knowledge graph and adaptive learning loop
- Voice, vision, web, automation, and system-control service abstractions
- A FastAPI developer surface and an optional PyQt dashboard
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

4. Submit a command:

```powershell
curl -X POST http://127.0.0.1:8000/command -H "Content-Type: application/json" -d "{\"text\":\"Jarvis remember that my favorite editor is VS Code\"}"
```

## Optional Multimodal Features

Install `requirements-optional.txt` to enable heavier voice, vision, and UI integrations such as Porcupine, Whisper, OpenCV, and PyQt.

## Architecture

The runtime is organized under `jarvis/`:

- `core`: configuration, lifecycle, event bus, logging, shared models
- `brain`: task planning and reasoning loops
- `agents`: specialist agents coordinated by the commander
- `memory`: long-term storage and semantic recall
- `voice`: wake word, VAD, STT, TTS, and orchestration
- `vision`: OCR and visual context extraction
- `system_control`: safe OS and shell integration
- `automation`: scheduled jobs and background workflows
- `web_intelligence`: research, news, weather, and search providers
- `plugins`: plugin SDK and auto-loadable integrations
- `api`: FastAPI routes for developer access
- `ui`: optional PyQt dashboard

## Safety Model

JARVIS uses:

- a command risk assessor
- configurable confirmation gates for dangerous actions
- sandbox-aware shell execution
- voice identity verification hooks
- permission categories for tools and agents

## Persistence

By default JARVIS stores runtime data under `.jarvis_runtime/` in the project root:

- `jarvis.db`: structured memory and task history
- `semantic_memory.json`: semantic index for recall
- `jarvis.log`: runtime logs

## Next Steps

- Configure API keys or external providers in `jarvis/config/settings.yaml`
- Extend `jarvis/plugins/base.py` to add new capabilities
- Replace fallback providers with GPU-backed local or cloud models
