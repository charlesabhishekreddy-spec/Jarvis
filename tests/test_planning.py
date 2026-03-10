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
