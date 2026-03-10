import unittest

from jarvis.brain.planning import TaskPlanner
from jarvis.core.models import CommandRequest


class TaskPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = TaskPlanner()

    def test_daily_reminder_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis remind me every day at 8am to stretch"))
        self.assertEqual(plan.steps[0].agent_hint, "automation")
        self.assertEqual(plan.steps[0].metadata["schedule_type"], "daily")
        self.assertEqual(plan.steps[0].metadata["time_of_day"], "08:00:00")

    def test_status_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis show system status"))
        self.assertEqual(plan.steps[0].agent_hint, "system")
        self.assertEqual(plan.steps[0].metadata["action"], "resource_usage")

    def test_startup_install_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis enable startup in background mode"))
        self.assertEqual(plan.steps[0].agent_hint, "security")
        self.assertEqual(plan.steps[1].agent_hint, "system")
        self.assertEqual(plan.steps[1].metadata["action"], "install_startup")
        self.assertEqual(plan.steps[1].metadata["mode"], "background")

    def test_mouse_click_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis double click at 120, 340"))
        self.assertEqual(plan.steps[0].agent_hint, "security")
        self.assertEqual(plan.steps[1].metadata["action"], "mouse_click")
        self.assertEqual(plan.steps[1].metadata["clicks"], 2)
        self.assertEqual(plan.steps[1].metadata["x"], 120)
        self.assertEqual(plan.steps[1].metadata["y"], 340)

    def test_keyboard_press_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis press ctrl+shift+s"))
        self.assertEqual(plan.steps[1].metadata["action"], "keyboard_press")
        self.assertEqual(plan.steps[1].metadata["keys"], ["ctrl", "shift", "s"])
