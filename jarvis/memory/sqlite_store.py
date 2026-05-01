from __future__ import annotations

import asyncio
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from jarvis.core.models import ActivityRecord, CommandRequest, CommandResponse, TaskPlan


class SQLiteMemoryStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    def _initialize_sync(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    request_id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    item_id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    plan_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS activities (
                    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    node_key TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_edges (
                    edge_key TEXT PRIMARY KEY,
                    subject_key TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_key TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS patterns (
                    pattern TEXT PRIMARY KEY,
                    count INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_jobs (
                    job_id TEXT PRIMARY KEY,
                    message TEXT NOT NULL,
                    cadence TEXT NOT NULL,
                    run_at TEXT NOT NULL,
                    day_of_week INTEGER NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_triggered_at TEXT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS confirmations (
                    confirmation_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    recommended_action TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT NULL,
                    decision_note TEXT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS project_contexts (
                    project_id TEXT PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS proactive_suggestions (
                    suggestion_id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS goals (
                    goal_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    title_key TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    project_id TEXT NULL,
                    next_action TEXT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    title_key TEXT NOT NULL,
                    goal_id TEXT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_steps (
                    step_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    step_order INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    command_text TEXT NOT NULL,
                    depends_on_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT NULL,
                    request_id TEXT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_goals_status_updated
                ON goals (status, updated_at DESC)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_goals_title_key
                ON goals (title_key)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workflows_status_updated
                ON workflows (status, updated_at DESC)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workflows_title_key
                ON workflows (title_key)
                """
            )
            connection.commit()

    async def save_conversation(self, request: CommandRequest, response: CommandResponse) -> None:
        await asyncio.to_thread(self._save_conversation_sync, request, response)

    def _save_conversation_sync(self, request: CommandRequest, response: CommandResponse) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO conversations (
                    request_id, text, source, metadata_json, response_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    request.request_id,
                    request.text,
                    request.source,
                    json.dumps(request.metadata),
                    json.dumps(
                        {
                            "status": response.status.value,
                            "message": response.message,
                            "task_id": response.task_id,
                            "data": response.data,
                            "timestamp": response.timestamp.isoformat(),
                        }
                    ),
                    request.timestamp.isoformat(),
                ),
            )
            connection.commit()

    async def save_memory(
        self,
        item_id: str,
        category: str,
        content: str,
        metadata: dict[str, Any],
        created_at: str,
    ) -> None:
        await asyncio.to_thread(self._save_memory_sync, item_id, category, content, metadata, created_at)

    def _save_memory_sync(
        self,
        item_id: str,
        category: str,
        content: str,
        metadata: dict[str, Any],
        created_at: str,
    ) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO memories (item_id, category, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_id, category, content, json.dumps(metadata), created_at),
            )
            connection.commit()

    async def save_task(self, plan: TaskPlan) -> None:
        await asyncio.to_thread(self._save_task_sync, plan)

    def _save_task_sync(self, plan: TaskPlan) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO tasks (plan_id, goal, status, plan_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (plan.plan_id, plan.goal, plan.status.value, json.dumps(plan.to_dict()), plan.updated_at.isoformat()),
            )
            connection.commit()

    async def log_activity(self, activity: ActivityRecord) -> None:
        await asyncio.to_thread(self._log_activity_sync, activity)

    def _log_activity_sync(self, activity: ActivityRecord) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT INTO activities (category, message, details_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (activity.category, activity.message, json.dumps(activity.details), activity.timestamp.isoformat()),
            )
            connection.commit()

    async def recent_conversations(self, limit: int = 20) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._recent_conversations_sync, limit)

    def _recent_conversations_sync(self, limit: int) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            cursor = connection.execute(
                """
                SELECT request_id, text, source, metadata_json, response_json, created_at
                FROM conversations
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
        return [
            {
                "request_id": row[0],
                "text": row[1],
                "source": row[2],
                "metadata": json.loads(row[3]),
                "response": json.loads(row[4]),
                "created_at": row[5],
            }
            for row in rows
        ]

    async def recent_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._recent_tasks_sync, limit)

    def _recent_tasks_sync(self, limit: int) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            cursor = connection.execute(
                """
                SELECT plan_json FROM tasks
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
        return [json.loads(row[0]) for row in rows]

    async def recent_activities(self, limit: int = 50) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._recent_activities_sync, limit)

    def _recent_activities_sync(self, limit: int) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            cursor = connection.execute(
                """
                SELECT category, message, details_json, created_at
                FROM activities
                ORDER BY activity_id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
        return [
            {
                "category": row[0],
                "message": row[1],
                "details": json.loads(row[2]),
                "created_at": row[3],
            }
            for row in rows
        ]

    async def upsert_graph_node(
        self,
        node_key: str,
        label: str,
        node_type: str,
        metadata: dict[str, Any],
        updated_at: str,
    ) -> None:
        await asyncio.to_thread(self._upsert_graph_node_sync, node_key, label, node_type, metadata, updated_at)

    def _upsert_graph_node_sync(
        self,
        node_key: str,
        label: str,
        node_type: str,
        metadata: dict[str, Any],
        updated_at: str,
    ) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO graph_nodes (node_key, label, node_type, metadata_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (node_key, label, node_type, json.dumps(metadata), updated_at),
            )
            connection.commit()

    async def upsert_graph_edge(
        self,
        edge_key: str,
        subject_key: str,
        predicate: str,
        object_key: str,
        metadata: dict[str, Any],
        updated_at: str,
    ) -> None:
        await asyncio.to_thread(
            self._upsert_graph_edge_sync,
            edge_key,
            subject_key,
            predicate,
            object_key,
            metadata,
            updated_at,
        )

    def _upsert_graph_edge_sync(
        self,
        edge_key: str,
        subject_key: str,
        predicate: str,
        object_key: str,
        metadata: dict[str, Any],
        updated_at: str,
    ) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO graph_edges (edge_key, subject_key, predicate, object_key, metadata_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (edge_key, subject_key, predicate, object_key, json.dumps(metadata), updated_at),
            )
            connection.commit()

    async def graph_snapshot(self, limit: int = 25) -> dict[str, Any]:
        return await asyncio.to_thread(self._graph_snapshot_sync, limit)

    def _graph_snapshot_sync(self, limit: int) -> dict[str, Any]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            node_rows = connection.execute(
                """
                SELECT node_key, label, node_type, metadata_json, updated_at
                FROM graph_nodes
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            edge_rows = connection.execute(
                """
                SELECT edge_key, subject_key, predicate, object_key, metadata_json, updated_at
                FROM graph_edges
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return {
            "nodes": [
                {
                    "node_key": row[0],
                    "label": row[1],
                    "node_type": row[2],
                    "metadata": json.loads(row[3]),
                    "updated_at": row[4],
                }
                for row in node_rows
            ],
            "edges": [
                {
                    "edge_key": row[0],
                    "subject_key": row[1],
                    "predicate": row[2],
                    "object_key": row[3],
                    "metadata": json.loads(row[4]),
                    "updated_at": row[5],
                }
                for row in edge_rows
            ],
        }

    async def record_pattern(self, pattern: str, metadata: dict[str, Any], updated_at: str) -> None:
        await asyncio.to_thread(self._record_pattern_sync, pattern, metadata, updated_at)

    def _record_pattern_sync(self, pattern: str, metadata: dict[str, Any], updated_at: str) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            existing = connection.execute("SELECT count FROM patterns WHERE pattern = ?", (pattern,)).fetchone()
            count = (existing[0] if existing else 0) + 1
            connection.execute(
                """
                INSERT OR REPLACE INTO patterns (pattern, count, metadata_json, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (pattern, count, json.dumps(metadata), updated_at),
            )
            connection.commit()

    async def top_patterns(self, limit: int = 10) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._top_patterns_sync, limit)

    def _top_patterns_sync(self, limit: int) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            rows = connection.execute(
                """
                SELECT pattern, count, metadata_json, updated_at
                FROM patterns
                ORDER BY count DESC, updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "pattern": row[0],
                "count": row[1],
                "metadata": json.loads(row[2]),
                "updated_at": row[3],
            }
            for row in rows
        ]

    async def save_automation_job(self, job: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_automation_job_sync, job)

    def _save_automation_job_sync(self, job: dict[str, Any]) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO automation_jobs (
                    job_id, message, cadence, run_at, day_of_week, status, created_at, updated_at, last_triggered_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["job_id"],
                    job["message"],
                    job["cadence"],
                    job["run_at"],
                    job.get("day_of_week"),
                    job["status"],
                    job["created_at"],
                    job["updated_at"],
                    job.get("last_triggered_at"),
                    json.dumps(job.get("metadata", {})),
                ),
            )
            connection.commit()

    async def automation_jobs(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._automation_jobs_sync, status, limit)

    def _automation_jobs_sync(self, status: str | None, limit: int) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            if status:
                rows = connection.execute(
                    """
                    SELECT job_id, message, cadence, run_at, day_of_week, status, created_at, updated_at, last_triggered_at, metadata_json
                    FROM automation_jobs
                    WHERE status = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT job_id, message, cadence, run_at, day_of_week, status, created_at, updated_at, last_triggered_at, metadata_json
                    FROM automation_jobs
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [
            {
                "job_id": row[0],
                "message": row[1],
                "cadence": row[2],
                "run_at": row[3],
                "day_of_week": row[4],
                "status": row[5],
                "created_at": row[6],
                "updated_at": row[7],
                "last_triggered_at": row[8],
                "metadata": json.loads(row[9]),
            }
            for row in rows
        ]

    async def save_confirmation(self, confirmation: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_confirmation_sync, confirmation)

    def _save_confirmation_sync(self, confirmation: dict[str, Any]) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO confirmations (
                    confirmation_id, request_id, text, source, risk_level, reason, recommended_action,
                    metadata_json, status, created_at, resolved_at, decision_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    confirmation["confirmation_id"],
                    confirmation["request_id"],
                    confirmation["text"],
                    confirmation["source"],
                    confirmation["risk_level"],
                    confirmation["reason"],
                    confirmation["recommended_action"],
                    json.dumps(confirmation.get("metadata", {})),
                    confirmation["status"],
                    confirmation["created_at"],
                    confirmation.get("resolved_at"),
                    confirmation.get("decision_note"),
                ),
            )
            connection.commit()

    async def get_confirmation(self, confirmation_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_confirmation_sync, confirmation_id)

    def _get_confirmation_sync(self, confirmation_id: str) -> dict[str, Any] | None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            row = connection.execute(
                """
                SELECT confirmation_id, request_id, text, source, risk_level, reason, recommended_action,
                       metadata_json, status, created_at, resolved_at, decision_note
                FROM confirmations
                WHERE confirmation_id = ?
                """,
                (confirmation_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "confirmation_id": row[0],
            "request_id": row[1],
            "text": row[2],
            "source": row[3],
            "risk_level": row[4],
            "reason": row[5],
            "recommended_action": row[6],
            "metadata": json.loads(row[7]),
            "status": row[8],
            "created_at": row[9],
            "resolved_at": row[10],
            "decision_note": row[11],
        }

    async def confirmations(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._confirmations_sync, status, limit)

    def _confirmations_sync(self, status: str | None, limit: int) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            if status:
                rows = connection.execute(
                    """
                    SELECT confirmation_id, request_id, text, source, risk_level, reason, recommended_action,
                           metadata_json, status, created_at, resolved_at, decision_note
                    FROM confirmations
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT confirmation_id, request_id, text, source, risk_level, reason, recommended_action,
                           metadata_json, status, created_at, resolved_at, decision_note
                    FROM confirmations
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [
            {
                "confirmation_id": row[0],
                "request_id": row[1],
                "text": row[2],
                "source": row[3],
                "risk_level": row[4],
                "reason": row[5],
                "recommended_action": row[6],
                "metadata": json.loads(row[7]),
                "status": row[8],
                "created_at": row[9],
                "resolved_at": row[10],
                "decision_note": row[11],
            }
            for row in rows
        ]

    async def save_project_context(self, context: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_project_context_sync, context)

    def _save_project_context_sync(self, context: dict[str, Any]) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO project_contexts (
                    project_id, project_name, summary, status, metadata_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    context["project_id"],
                    context["project_name"],
                    context["summary"],
                    context["status"],
                    json.dumps(context.get("metadata", {})),
                    context["updated_at"],
                ),
            )
            connection.commit()

    async def project_context(self, project_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._project_context_sync, project_id)

    def _project_context_sync(self, project_id: str) -> dict[str, Any] | None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            row = connection.execute(
                """
                SELECT project_id, project_name, summary, status, metadata_json, updated_at
                FROM project_contexts
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "project_id": row[0],
            "project_name": row[1],
            "summary": row[2],
            "status": row[3],
            "metadata": json.loads(row[4]),
            "updated_at": row[5],
        }

    async def project_contexts(self, status: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._project_contexts_sync, status, limit)

    def _project_contexts_sync(self, status: str | None, limit: int) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            if status:
                rows = connection.execute(
                    """
                    SELECT project_id, project_name, summary, status, metadata_json, updated_at
                    FROM project_contexts
                    WHERE status = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT project_id, project_name, summary, status, metadata_json, updated_at
                    FROM project_contexts
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [
            {
                "project_id": row[0],
                "project_name": row[1],
                "summary": row[2],
                "status": row[3],
                "metadata": json.loads(row[4]),
                "updated_at": row[5],
            }
            for row in rows
        ]

    async def replace_proactive_suggestions(self, suggestions: list[dict[str, Any]]) -> None:
        await asyncio.to_thread(self._replace_proactive_suggestions_sync, suggestions)

    def _replace_proactive_suggestions_sync(self, suggestions: list[dict[str, Any]]) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute("DELETE FROM proactive_suggestions")
            connection.executemany(
                """
                INSERT INTO proactive_suggestions (
                    suggestion_id, category, title, detail, priority, status, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        suggestion["suggestion_id"],
                        suggestion["category"],
                        suggestion["title"],
                        suggestion["detail"],
                        suggestion["priority"],
                        suggestion["status"],
                        json.dumps(suggestion.get("metadata", {})),
                        suggestion["created_at"],
                        suggestion["updated_at"],
                    )
                    for suggestion in suggestions
                ],
            )
            connection.commit()

    async def proactive_suggestions(self, status: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._proactive_suggestions_sync, status, limit)

    def _proactive_suggestions_sync(self, status: str | None, limit: int) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            if status:
                rows = connection.execute(
                    """
                    SELECT suggestion_id, category, title, detail, priority, status, metadata_json, created_at, updated_at
                    FROM proactive_suggestions
                    WHERE status = ?
                    ORDER BY priority DESC, updated_at DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT suggestion_id, category, title, detail, priority, status, metadata_json, created_at, updated_at
                    FROM proactive_suggestions
                    ORDER BY priority DESC, updated_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [
            {
                "suggestion_id": row[0],
                "category": row[1],
                "title": row[2],
                "detail": row[3],
                "priority": row[4],
                "status": row[5],
                "metadata": json.loads(row[6]),
                "created_at": row[7],
                "updated_at": row[8],
            }
            for row in rows
        ]

    async def save_goal(self, goal: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_goal_sync, goal)

    def _save_goal_sync(self, goal: dict[str, Any]) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO goals (
                    goal_id, title, title_key, detail, priority, status, project_id, next_action,
                    metadata_json, created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    goal["goal_id"],
                    goal["title"],
                    self._title_key(goal["title"]),
                    goal["detail"],
                    int(goal.get("priority", 50)),
                    goal["status"],
                    goal.get("project_id"),
                    goal.get("next_action"),
                    json.dumps(goal.get("metadata", {})),
                    goal["created_at"],
                    goal["updated_at"],
                    goal.get("completed_at"),
                ),
            )
            connection.commit()

    async def goal(self, goal_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._goal_sync, goal_id)

    def _goal_sync(self, goal_id: str) -> dict[str, Any] | None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            row = connection.execute(
                """
                SELECT goal_id, title, detail, priority, status, project_id, next_action, metadata_json,
                       created_at, updated_at, completed_at
                FROM goals
                WHERE goal_id = ?
                """,
                (goal_id,),
            ).fetchone()
        return self._goal_row_to_dict(row)

    async def find_goal(self, title: str, statuses: list[str] | None = None) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._find_goal_sync, title, statuses)

    def _find_goal_sync(self, title: str, statuses: list[str] | None) -> dict[str, Any] | None:
        title_key = self._title_key(title)
        status_clause, params = self._goal_status_clause(statuses)
        with closing(sqlite3.connect(self.db_path)) as connection:
            exact = connection.execute(
                f"""
                SELECT goal_id, title, detail, priority, status, project_id, next_action, metadata_json,
                       created_at, updated_at, completed_at
                FROM goals
                WHERE title_key = ? {status_clause}
                ORDER BY priority DESC, updated_at DESC
                LIMIT 1
                """,
                (title_key, *params),
            ).fetchone()
            if exact is not None:
                return self._goal_row_to_dict(exact)
            partial = connection.execute(
                f"""
                SELECT goal_id, title, detail, priority, status, project_id, next_action, metadata_json,
                       created_at, updated_at, completed_at
                FROM goals
                WHERE (title_key LIKE ? OR ? LIKE '%' || title_key || '%') {status_clause}
                ORDER BY priority DESC, updated_at DESC
                LIMIT 1
                """,
                (f"%{title_key}%", title_key, *params),
            ).fetchone()
        return self._goal_row_to_dict(partial)

    async def goals(self, status: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._goals_sync, status, limit)

    def _goals_sync(self, status: str | None, limit: int) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            if status:
                rows = connection.execute(
                    """
                    SELECT goal_id, title, detail, priority, status, project_id, next_action, metadata_json,
                           created_at, updated_at, completed_at
                    FROM goals
                    WHERE status = ?
                    ORDER BY priority DESC, updated_at DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT goal_id, title, detail, priority, status, project_id, next_action, metadata_json,
                           created_at, updated_at, completed_at
                    FROM goals
                    ORDER BY priority DESC, updated_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [self._goal_row_to_dict(row) for row in rows if row is not None]

    def _goal_status_clause(self, statuses: list[str] | None) -> tuple[str, list[str]]:
        if not statuses:
            return "", []
        placeholders = ", ".join("?" for _ in statuses)
        return f" AND status IN ({placeholders})", list(statuses)

    def _goal_row_to_dict(self, row: Any) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "goal_id": row[0],
            "title": row[1],
            "detail": row[2],
            "priority": row[3],
            "status": row[4],
            "project_id": row[5],
            "next_action": row[6],
            "metadata": json.loads(row[7]),
            "created_at": row[8],
            "updated_at": row[9],
            "completed_at": row[10],
        }

    def _title_key(self, title: str) -> str:
        return " ".join(title.lower().split())

    async def save_workflow(self, workflow: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_workflow_sync, workflow)

    def _save_workflow_sync(self, workflow: dict[str, Any]) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO workflows (
                    workflow_id, title, title_key, goal_id, status, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow["workflow_id"],
                    workflow["title"],
                    self._title_key(workflow["title"]),
                    workflow.get("goal_id"),
                    workflow["status"],
                    json.dumps(workflow.get("metadata", {})),
                    workflow["created_at"],
                    workflow["updated_at"],
                ),
            )
            connection.execute("DELETE FROM workflow_steps WHERE workflow_id = ?", (workflow["workflow_id"],))
            connection.executemany(
                """
                INSERT INTO workflow_steps (
                    step_id, workflow_id, step_order, title, command_text, depends_on_json, status, result, request_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        step["step_id"],
                        workflow["workflow_id"],
                        index,
                        step["title"],
                        step["command_text"],
                        json.dumps(step.get("depends_on", [])),
                        step["status"],
                        step.get("result"),
                        step.get("request_id"),
                    )
                    for index, step in enumerate(workflow.get("steps", []))
                ],
            )
            connection.commit()

    async def workflow(self, workflow_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._workflow_sync, workflow_id)

    def _workflow_sync(self, workflow_id: str) -> dict[str, Any] | None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            workflow_row = connection.execute(
                """
                SELECT workflow_id, title, goal_id, status, metadata_json, created_at, updated_at
                FROM workflows
                WHERE workflow_id = ?
                """,
                (workflow_id,),
            ).fetchone()
            if workflow_row is None:
                return None
            step_rows = connection.execute(
                """
                SELECT step_id, title, command_text, depends_on_json, status, result, request_id
                FROM workflow_steps
                WHERE workflow_id = ?
                ORDER BY step_order ASC
                """,
                (workflow_id,),
            ).fetchall()
        return self._workflow_rows_to_dict(workflow_row, step_rows)

    async def find_workflow(self, title: str, statuses: list[str] | None = None) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._find_workflow_sync, title, statuses)

    def _find_workflow_sync(self, title: str, statuses: list[str] | None) -> dict[str, Any] | None:
        title_key = self._title_key(title)
        status_clause, params = self._goal_status_clause(statuses)
        with closing(sqlite3.connect(self.db_path)) as connection:
            row = connection.execute(
                f"""
                SELECT workflow_id, title, goal_id, status, metadata_json, created_at, updated_at
                FROM workflows
                WHERE (title_key = ? OR title_key LIKE ? OR ? LIKE '%' || title_key || '%') {status_clause}
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (title_key, f"%{title_key}%", title_key, *params),
            ).fetchone()
            if row is None:
                return None
            step_rows = connection.execute(
                """
                SELECT step_id, title, command_text, depends_on_json, status, result, request_id
                FROM workflow_steps
                WHERE workflow_id = ?
                ORDER BY step_order ASC
                """,
                (row[0],),
            ).fetchall()
        return self._workflow_rows_to_dict(row, step_rows)

    async def workflows(self, status: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._workflows_sync, status, limit)

    def _workflows_sync(self, status: str | None, limit: int) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            if status:
                workflow_rows = connection.execute(
                    """
                    SELECT workflow_id, title, goal_id, status, metadata_json, created_at, updated_at
                    FROM workflows
                    WHERE status = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            else:
                workflow_rows = connection.execute(
                    """
                    SELECT workflow_id, title, goal_id, status, metadata_json, created_at, updated_at
                    FROM workflows
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            workflow_ids = [row[0] for row in workflow_rows]
            step_rows = connection.execute(
                f"""
                SELECT step_id, workflow_id, title, command_text, depends_on_json, status, result, request_id, step_order
                FROM workflow_steps
                WHERE workflow_id IN ({", ".join("?" for _ in workflow_ids)}) 
                ORDER BY workflow_id ASC, step_order ASC
                """ if workflow_ids else "SELECT step_id, workflow_id, title, command_text, depends_on_json, status, result, request_id, step_order FROM workflow_steps WHERE 1 = 0",
                workflow_ids,
            ).fetchall() if workflow_ids else []

        steps_by_workflow: dict[str, list[Any]] = {}
        for row in step_rows:
            steps_by_workflow.setdefault(row[1], []).append(row)
        return [
            self._workflow_rows_to_dict(row, steps_by_workflow.get(row[0], []), workflow_row_has_id=False)
            for row in workflow_rows
        ]

    def _workflow_rows_to_dict(
        self,
        workflow_row: Any,
        step_rows: list[Any],
        workflow_row_has_id: bool = True,
    ) -> dict[str, Any]:
        if workflow_row_has_id:
            workflow_id, title, goal_id, status, metadata_json, created_at, updated_at = workflow_row
            steps = [
                {
                    "step_id": row[0],
                    "title": row[1],
                    "command_text": row[2],
                    "depends_on": json.loads(row[3]),
                    "status": row[4],
                    "result": row[5],
                    "request_id": row[6],
                }
                for row in step_rows
            ]
        else:
            workflow_id, title, goal_id, status, metadata_json, created_at, updated_at = workflow_row
            steps = [
                {
                    "step_id": row[0],
                    "title": row[2],
                    "command_text": row[3],
                    "depends_on": json.loads(row[4]),
                    "status": row[5],
                    "result": row[6],
                    "request_id": row[7],
                }
                for row in step_rows
            ]
        return {
            "workflow_id": workflow_id,
            "title": title,
            "goal_id": goal_id,
            "status": status,
            "metadata": json.loads(metadata_json),
            "created_at": created_at,
            "updated_at": updated_at,
            "steps": steps,
        }
