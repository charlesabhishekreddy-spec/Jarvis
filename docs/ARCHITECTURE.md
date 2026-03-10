# JARVIS Architecture

## Runtime

`JarvisRuntime` is the composition root. It owns:

- shared settings and logging
- the async event bus
- memory, security, automation, web, vision, and voice services
- local-first intelligence providers and adaptive learning
- durable automation with restart restoration
- the tool registry
- the plugin loader
- the reasoning engine

## Command Flow

1. A command enters through the API, CLI, or voice pipeline.
2. Security assesses risk and may require confirmation.
3. The planner creates a `TaskPlan`.
4. The reasoning engine routes each `TaskStep` to a specialist agent.
5. Agents call tools and services through the shared context.
6. Results are persisted to SQLite and the semantic memory index.
7. Events and activity records are emitted for observability.

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
- `brain.learning` records repeated user intents and extracts preferences into the knowledge graph.
- Commander and research flows use the intelligence layer to synthesize summaries and reports.

## Safety

- `security.policy` classifies commands by risk level.
- `security.sandbox` restricts shell work directories.
- `security.manager` centralizes risk checks, permissions, and identity hooks.

## Extensibility

- Tools are registered in `jarvis.tools.registry`.
- Plugins implement `JarvisPlugin` and can use `plugins.sdk.PluginAPI` to register tools, subscribe to events, log activity, and store memory.
- Example plugins in `jarvis/plugins/examples` show event hooks and custom tool registration.
- The FastAPI layer exposes status, command execution, memory search, jobs, event streams, dashboard assets, and plugin discovery for external developers.
