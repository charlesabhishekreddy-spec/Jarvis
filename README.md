# JARVIS

JARVIS (Just A Rather Very Intelligent System) is a modular local-first AI assistant platform designed to run as a persistent operating layer on a user's computer.

This repository provides:

- An async runtime with lifecycle management, observability, and a message bus
- Multi-agent planning and execution
- Gemini-first intelligence with heuristic fallback and optional Ollama compatibility
- Tool-planned autonomous execution for workspace and system requests
- Persistent memory with SQLite and a local semantic index
- A personal knowledge graph and adaptive learning loop
- Durable automation jobs that restore after runtime restart
- Background command queue with async submission and cancellation
- Windows startup registration controls for boot persistence
- Desktop automation primitives for mouse and keyboard control
- Process inspection and confirmation-gated process termination
- Window inspection plus focus, minimize, and maximize controls
- Proactive suggestions and persistent project context
- Persistent goals with background next-action review
- Durable workflow orchestration on top of the command queue
- Workflow restoration after runtime restart
- Controllable always-on voice runtime with optional microphone capture
- Vision runtime with screen capture, camera capture, OCR status, and artifact saving
- Dependency-aware workflow planning for compound requests
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

3. Configure Gemini:

```powershell
$env:JARVIS_GEMINI_API_KEY="your-api-key"
```

4. Start the API-backed runtime:

```powershell
python -m jarvis.main --api
```

Then open `http://127.0.0.1:8000/dashboard`.

5. Submit a command:

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
- Intelligence provider inspection: `GET /intelligence`, `POST /intelligence/respond`
- Voice controls: `GET /voice`, `POST /voice/start`, `POST /voice/stop`, `POST /voice/simulate`, `POST /voice/text`
- Vision controls: `GET /vision`, `POST /vision/screen`, `POST /vision/camera`
- Process controls: `GET /processes`, `POST /processes/terminate`
- Window controls: `GET /windows`, `POST /windows/focus`, `POST /windows/minimize`, `POST /windows/maximize`
- Project context: `GET /memory/projects`
- Goals: `GET /goals`, `POST /goals`, `POST /goals/review`, `POST /goals/{goal_id}/status`
- Workflows: `GET /workflows`, `POST /workflows`, `POST /workflows/{workflow_id}/run`, `POST /workflows/{workflow_id}/cancel`
- Proactive suggestions: `GET /suggestions`
- Startup controls: `GET /startup`, `POST /startup/install`, `POST /startup/uninstall`
- Job inspection: `GET /jobs`
- Job cancellation: `POST /jobs/{job_id}/cancel`

The browser dashboard now includes an intelligence console for sending direct Gemini prompts with optional JSON context.
The dashboard also surfaces voice and vision runtime state, running processes, desktop windows, proactive suggestions, active project context, persistent goals, and stored workflows, including queued workflow state after restart.

## Architecture

The runtime is organized under `jarvis/`:

- `core`: configuration, lifecycle, event bus, logging, shared models
- `brain`: task planning and reasoning loops
- `agents`: specialist agents coordinated by the commander
- `memory`: long-term storage, semantic recall, project context, suggestions, and goals
- `brain/intelligence.py`: local-first reasoning providers and summarization
- `agents/autonomous.py`: tool-driven fallback agent for generic workspace/system tasks
- `brain/learning.py`: adaptive behavior tracking and insights
- `brain/proactive.py`: background goal review and next-action refresh
- `automation/orchestration.py`: durable workflow storage and queued step execution
- `voice/audio.py`: optional microphone capture backend
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

Process inspection and termination are also available:

```powershell
python -m jarvis.main --once "Jarvis list running processes"
python -m jarvis.main --once "Jarvis stop process 1234"
```

Window inspection and control are also available:

```powershell
python -m jarvis.main --once "Jarvis list open windows"
python -m jarvis.main --once "Jarvis focus window Visual Studio Code"
python -m jarvis.main --once "Jarvis minimize window Microsoft Edge"
```

Voice commands can be simulated through the API or dashboard even when the live microphone stack is unavailable:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/voice
Invoke-RestMethod -Uri http://127.0.0.1:8000/voice/simulate -Method Post -ContentType "application/json" -Body '{"text":"Hey Jarvis what are we working on"}'
```

Vision captures are also exposed through the API and dashboard:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/vision
Invoke-RestMethod -Uri http://127.0.0.1:8000/vision/screen -Method Post -ContentType "application/json" -Body '{"save_artifact":true,"include_ocr":true,"label":"ops"}'
Invoke-RestMethod -Uri http://127.0.0.1:8000/vision/camera -Method Post -ContentType "application/json" -Body '{"save_artifact":true,"include_ocr":false,"label":"desk"}'
```

Compound requests now build explicit workflow plans with dependencies:

```powershell
python -m jarvis.main --once "Jarvis remember that my task board is Linear then what did I say about task board"
```

Persistent goal tracking is also available through natural language:

```powershell
python -m jarvis.main --once "Jarvis track goal ship the API upgrade"
python -m jarvis.main --once "Jarvis what should I focus on"
python -m jarvis.main --once "Jarvis complete goal ship the API upgrade"
```

Stored workflows can orchestrate multiple commands across the existing agents:

```powershell
python -m jarvis.main --once "Jarvis create workflow research renewable energy then prepare a report then remind me tomorrow at 8am to review it"
python -m jarvis.main --once "Jarvis list workflows"
python -m jarvis.main --once "Jarvis run workflow research renewable energy and 2 more steps"
```

## Persistence

By default JARVIS stores runtime data under `.jarvis_runtime/` in the project root:

- `jarvis.db`: structured memory and task history
- `semantic_memory.json`: semantic index for recall
- `jarvis.log`: runtime logs

## Next Steps

- Configure `JARVIS_GEMINI_API_KEY` or switch providers in `jarvis/config/settings.yaml`
- Extend `jarvis/plugins/base.py` and `jarvis/plugins/sdk.py` to add new capabilities
- Replace fallback providers with GPU-backed local or cloud models
