# JARVIS Architecture

## Runtime

`JarvisRuntime` is the composition root. It owns:

- shared settings and logging
- the async event bus
- memory, security, automation, web, vision, and voice services
- local-first intelligence providers and adaptive learning
- durable automation with restart restoration
- startup persistence management for Windows logon tasks
- the tool registry
- the plugin loader
- the reasoning engine

## Command Flow

1. A command enters through the API, CLI, or voice pipeline.
2. Security assesses risk and may require confirmation.
3. Commands may run immediately or enter the background command queue.
4. The planner creates a `TaskPlan`.
5. The reasoning engine routes each `TaskStep` to a specialist agent.
6. Agents call tools and services through the shared context.
7. Results are persisted to SQLite and the semantic memory index.
8. Events and activity records are emitted for observability.

## Background Execution

- `core.task_queue` provides queued execution, live status, and cancellation.
- Queue records expose queued, running, completed, failed, cancelled, and confirmation-required states.
- The dashboard and API can inspect recent execution records without blocking on command completion.

## Startup Persistence

- `system_control.startup` generates absolute launch commands for `main.py` and manages a Windows scheduled task named by configuration.
- Startup state is exposed through the runtime status snapshot, API, CLI, and dashboard.
- Startup install and uninstall requests are treated as risky system changes and flow through the confirmation gate when invoked through natural language.

## Automation

- Scheduled jobs are persisted in SQLite.
- On runtime startup, `automation.scheduler` restores scheduled jobs and resumes their timers.
- Job transitions emit `automation.scheduled`, `automation.restored`, `automation.triggered`, and `automation.cancelled` events.

## Memory

- Structured memory is stored in SQLite for conversations, tasks, activities, and explicit user facts.
- Semantic memory is stored in a JSON-backed local vector index using lexical cosine similarity.
- A lightweight knowledge graph is stored in SQLite as nodes and edges extracted from user statements.
- The semantic store is intentionally lightweight so the project runs locally before a heavier vector database is added.

## Intelligence

- `brain.intelligence` provides a heuristic local provider and an Ollama-compatible provider.
- `brain.intelligence` can also propose tool calls for generic file, workspace, memory, and system requests.
- `brain.learning` records repeated user intents and extracts preferences into the knowledge graph.
- Commander and research flows use the intelligence layer to synthesize summaries and reports.

## Autonomous Tool Use

- `agents.autonomous` is the fallback executor for generic requests that do not map to a specialist planner path.
- It asks the intelligence layer to propose tool calls, executes approved tools, and then synthesizes the result.
- Current built-in autonomous tool coverage includes file listing, file reading, process inspection, memory recall/storage, web search, and path opening.

## Safety

- `security.policy` classifies commands by risk level.
- `brain.reasoning` performs an additional plan-level confirmation pass for steps marked as sensitive.
- `security.sandbox` restricts shell work directories.
- `security.confirmations` persists approval requests and can resume approved actions through the background queue.
- `tools.registry` enforces tool-level confirmation requirements for direct tool execution.
- `security.manager` centralizes risk checks, permissions, and identity hooks.

## Desktop Control

- `system_control.desktop` provides optional mouse and keyboard automation through a pluggable backend.
- The default backend uses PyAutoGUI when installed; otherwise the runtime reports that desktop control is unavailable rather than simulating actions.
- Mouse movement, mouse clicks, typing, and shortcut presses are treated as confirmation-required actions in both planner-driven execution and direct tool calls.

## Extensibility

- Tools are registered in `jarvis.tools.registry`.
- Plugins implement `JarvisPlugin` and can use `plugins.sdk.PluginAPI` to register tools, subscribe to events, log activity, and store memory.
- Example plugins in `jarvis/plugins/examples` show event hooks and custom tool registration.
- The FastAPI layer exposes status, command execution, memory search, jobs, event streams, dashboard assets, and plugin discovery for external developers.
