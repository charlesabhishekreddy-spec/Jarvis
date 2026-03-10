from __future__ import annotations

import asyncio
import json
import sqlite3
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
        with sqlite3.connect(self.db_path) as connection:
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
            connection.commit()

    async def save_conversation(self, request: CommandRequest, response: CommandResponse) -> None:
        await asyncio.to_thread(self._save_conversation_sync, request, response)

    def _save_conversation_sync(self, request: CommandRequest, response: CommandResponse) -> None:
        with sqlite3.connect(self.db_path) as connection:
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
        with sqlite3.connect(self.db_path) as connection:
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
        with sqlite3.connect(self.db_path) as connection:
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
        with sqlite3.connect(self.db_path) as connection:
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
        with sqlite3.connect(self.db_path) as connection:
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
        with sqlite3.connect(self.db_path) as connection:
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
        with sqlite3.connect(self.db_path) as connection:
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
