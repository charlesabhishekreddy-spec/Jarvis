# JARVIS API

Primary runtime endpoints exposed by `jarvis/api/app.py`:

- `GET /health`: service states and runtime health
- `GET /status`: dashboard snapshot with tasks, activities, conversations, events, and insights
- `GET /dashboard`: browser control surface
- `POST /command`: execute a text command
- `POST /voice/text`: send a text transcript through the voice command path
- `POST /plan`: preview the generated task plan without executing it
- `GET /memory/search`: semantic memory lookup
- `GET /memory/graph`: knowledge graph snapshot
- `GET /insights`: learned command patterns and graph data
- `GET /tools`: list registered tools
- `POST /tools/{tool_name}`: execute a registered tool with JSON params
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
