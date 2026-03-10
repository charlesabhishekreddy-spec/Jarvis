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
