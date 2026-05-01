# JARVIS API

Primary runtime endpoints exposed by `jarvis/api/app.py`:

- `GET /health`: service states and runtime health
- `GET /status`: dashboard snapshot with tasks, activities, conversations, events, insights, and intelligence provider status
- `GET /dashboard`: browser control surface
- `GET /intelligence`: inspect the configured and active intelligence provider
- `POST /intelligence/respond`: send a direct prompt through the active intelligence provider
- `GET /startup`: inspect startup registration status and generated task commands
- `POST /startup/install`: register JARVIS to start on login
- `POST /startup/uninstall`: remove the startup registration
- `POST /command`: execute a text command
- `POST /command/async`: queue a command for background execution
- `POST /voice/text`: send a text transcript through the voice command path
- `GET /voice`: inspect voice runtime state and provider availability
- `POST /voice/start`: start the microphone listening loop when an audio provider is available
- `POST /voice/stop`: stop the microphone listening loop
- `POST /voice/simulate`: submit simulated heard speech through wake-word processing
- `GET /vision`: inspect screen, camera, and OCR provider availability plus recent capture state
- `POST /vision/screen`: capture the current screen, optionally save an artifact, and optionally run OCR
- `POST /vision/camera`: capture a webcam frame, optionally save an artifact, and optionally run OCR
- `GET /processes`: inspect running processes and basic CPU or memory telemetry
- `POST /processes/terminate`: route a process termination request through the normal confirmation-aware command flow
- `GET /windows`: inspect visible desktop windows and their titles
- `POST /windows/focus`: focus a matching window by title
- `POST /windows/minimize`: minimize a matching window by title
- `POST /windows/maximize`: maximize a matching window by title
- `POST /plan`: preview the generated task plan without executing it
- `GET /commands`: list recent queued/executed commands
- `GET /commands/{request_id}`: inspect a queued/executed command
- `POST /commands/{request_id}/cancel`: cancel a queued or running command
- `GET /confirmations`: list pending or resolved confirmation requests
- `GET /confirmations/{confirmation_id}`: inspect a single confirmation request
- `POST /confirmations/{confirmation_id}/approve`: approve a queued dangerous action
- `POST /confirmations/{confirmation_id}/reject`: reject a queued dangerous action
- `GET /memory/search`: semantic memory lookup
- `GET /memory/graph`: knowledge graph snapshot
- `GET /memory/projects`: active and recent project context records
- `GET /goals`: list persistent goals and next actions
- `POST /goals`: create a persistent goal
- `POST /goals/review`: force an immediate proactive goal review cycle
- `GET /goals/{goal_id}`: inspect a single goal
- `POST /goals/{goal_id}/status`: update goal status, priority, or next action
- `GET /workflows`: list stored workflows
- `POST /workflows`: create a stored workflow from a list of commands
- `GET /workflows/{workflow_id}`: inspect a workflow and its step state
- `POST /workflows/{workflow_id}/run`: execute a stored workflow through the background queue
- `POST /workflows/{workflow_id}/cancel`: cancel a running workflow

Queued or in-progress workflows are restored on runtime startup. Step state is normalized so interrupted queued/running steps resume from a pending state instead of staying stranded.
- `GET /suggestions`: proactive suggestions generated from recent work and patterns
- `GET /insights`: learned command patterns and graph data
- `GET /tools`: list registered tools
- `POST /tools/{tool_name}`: execute a registered tool with JSON params and optional `confirmed` flag
- `GET /plugins`: list loaded plugins
- `GET /jobs`: list scheduled automation jobs
- `POST /jobs/{job_id}/cancel`: cancel a scheduled job
- `GET /events`: read recent event bus history
- `GET /stream/events`: consume events over server-sent events
- `GET /ws/events`: consume events over WebSocket

Example command request:

```json
{
  "text": "Jarvis remember that my favorite editor is VS Code",
  "confirmed": false
}
```

Example startup install request:

```json
{
  "mode": "api",
  "host": "127.0.0.1",
  "port": 8000
}
```

Example confirmed desktop tool request:

```json
{
  "confirmed": true,
  "params": {
    "x": 100,
    "y": 200,
    "button": "left",
    "clicks": 1
  }
}
```

Example direct intelligence request:

```json
{
  "prompt": "Summarize the current assistant state in one sentence.",
  "context": {}
}
```

Example goal create request:

```json
{
  "title": "Ship the API upgrade",
  "detail": "Finalize the new platform endpoints",
  "priority": 80
}
```

Example workflow create request:

```json
{
  "title": "Editor memory workflow",
  "steps": [
    "remember that my editor is VS Code",
    "what did I say about editor"
  ]
}
```

Example voice simulation request:

```json
{
  "text": "Hey Jarvis what are we working on",
  "strict_wake": true,
  "confirmed": false
}
```

Example vision capture request:

```json
{
  "save_artifact": true,
  "include_ocr": true,
  "label": "ops"
}
```

Example process termination request:

```json
{
  "pid": 1234,
  "confirmed": false
}
```

Example window action request:

```json
{
  "title": "Visual Studio Code"
}
```

The browser dashboard includes a built-in intelligence console that submits to `POST /intelligence/respond`.
It also surfaces voice and vision runtime state, running processes, desktop windows, proactive suggestions, project context, goals, and workflows from `GET /voice`, `GET /vision`, `GET /processes`, `GET /windows`, `GET /suggestions`, `GET /memory/projects`, `GET /goals`, and `GET /workflows`.
