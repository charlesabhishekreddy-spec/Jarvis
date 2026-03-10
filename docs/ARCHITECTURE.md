# JARVIS Architecture

## Runtime

`JarvisRuntime` is the composition root. It owns:

- shared settings and logging
- the async event bus
- memory, security, automation, web, vision, and voice services
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

## Memory

- Structured memory is stored in SQLite for conversations, tasks, activities, and explicit user facts.
- Semantic memory is stored in a JSON-backed local vector index using lexical cosine similarity.
- The semantic store is intentionally lightweight so the project runs locally before a heavier vector database is added.

## Safety

- `security.policy` classifies commands by risk level.
- `security.sandbox` restricts shell work directories.
- `security.manager` centralizes risk checks, permissions, and identity hooks.

## Extensibility

- Tools are registered in `jarvis.tools.registry`.
- Plugins implement `JarvisPlugin` and are auto-loaded from `jarvis/plugins/examples` by default.
- The FastAPI layer exposes status, command execution, memory search, jobs, events, and plugin discovery for external developers.
