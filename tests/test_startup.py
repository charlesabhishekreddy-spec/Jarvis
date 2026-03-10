import unittest
from pathlib import Path

from jarvis.core.config import Settings
from jarvis.system_control.startup import StartupCommandResult, StartupManager


class StartupManagerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.settings = Settings()

    def test_plan_uses_absolute_main_script(self) -> None:
        manager = StartupManager(self.settings, platform_name="Windows")
        plan = manager.plan(mode="api", host="0.0.0.0", port=9001)

        self.assertTrue(Path(plan["launch_command"][1]).is_absolute())
        self.assertEqual(Path(plan["launch_command"][1]).name, "main.py")
        self.assertIn("--api", plan["launch_command"])
        self.assertIn("0.0.0.0", plan["launch_command"])
        self.assertIn("9001", plan["launch_command"])
        self.assertEqual(plan["install_command"][0], "schtasks")

    async def test_status_parses_windows_task_output(self) -> None:
        def runner(command: list[str]) -> StartupCommandResult:
            return StartupCommandResult(
                command=command,
                returncode=0,
                stdout="TaskName: \\JARVIS\nStatus: Ready\nLast Result: 0",
                stderr="",
            )

        manager = StartupManager(self.settings, platform_name="Windows", runner=runner)
        status = await manager.status(mode="api")

        self.assertTrue(status["installed"])
        self.assertEqual(status["details"]["status"], "Ready")
        self.assertEqual(status["details"]["last_result"], "0")

    async def test_non_windows_status_is_reported_as_unsupported(self) -> None:
        manager = StartupManager(self.settings, platform_name="Linux")
        status = await manager.status()

        self.assertFalse(status["supported"])
        self.assertFalse(status["installed"])

    async def test_uninstall_treats_missing_task_as_removed(self) -> None:
        def runner(command: list[str]) -> StartupCommandResult:
            return StartupCommandResult(
                command=command,
                returncode=1,
                stdout="",
                stderr="ERROR: The system cannot find the file specified.",
            )

        manager = StartupManager(self.settings, platform_name="Windows", runner=runner)
        result = await manager.uninstall()

        self.assertTrue(result["ok"])
        self.assertFalse(result["startup"]["installed"])
