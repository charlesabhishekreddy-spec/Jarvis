import shutil
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from jarvis.core.config import Settings
from jarvis.core.runtime import JarvisRuntime


class AutomationPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = Path.cwd() / ".test_runtime" / uuid4().hex
        self.tempdir.mkdir(parents=True, exist_ok=True)
        self.settings = Settings()
        self.settings.runtime.data_dir = str(self.tempdir)
        self.settings.memory.sqlite_path = str(self.tempdir / "jarvis.db")
        self.settings.memory.semantic_index_path = str(self.tempdir / "semantic_memory.json")
        self.settings.security.allowed_workdirs = [str(self.tempdir), str(Path.cwd())]

    async def asyncTearDown(self) -> None:
        shutil.rmtree(self.tempdir, ignore_errors=True)

    async def test_scheduled_job_restores_after_restart(self) -> None:
        runtime = JarvisRuntime(self.settings)
        await runtime.start()
        try:
            run_at = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(microsecond=0).isoformat()
            job = await runtime.automation.schedule_reminder("persistent reminder", run_at)
        finally:
            await runtime.stop()

        restarted = JarvisRuntime(self.settings)
        await restarted.start()
        try:
            jobs = restarted.automation.list_jobs()
            restored = next(item for item in jobs if item["job_id"] == job["job_id"])
            self.assertEqual(restored["message"], "persistent reminder")
            self.assertEqual(restored["status"], "scheduled")
        finally:
            await restarted.stop()

    async def test_cancel_job_persists_status(self) -> None:
        runtime = JarvisRuntime(self.settings)
        await runtime.start()
        try:
            run_at = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(microsecond=0).isoformat()
            job = await runtime.automation.schedule_reminder("cancel me", run_at)
            result = await runtime.automation.cancel_job(job["job_id"])
            self.assertTrue(result["ok"])
            stored_jobs = await runtime.memory.automation_jobs(limit=20)
            stored = next(item for item in stored_jobs if item["job_id"] == job["job_id"])
            self.assertEqual(stored["status"], "cancelled")
        finally:
            await runtime.stop()
