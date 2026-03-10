# JARVIS API

Primary runtime endpoints exposed by `jarvis/api/app.py`:

- `GET /health`: service states and runtime health
- `GET /status`: dashboard snapshot with tasks, activities, conversations, events, and insights
- `GET /dashboard`: browser control surface
- `GET /startup`: inspect startup registration status and generated task commands
- `POST /startup/install`: register JARVIS to start on login
- `POST /startup/uninstall`: remove the startup registration
- `POST /command`: execute a text command
- `POST /command/async`: queue a command for background execution
- `POST /voice/text`: send a text transcript through the voice command path
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
