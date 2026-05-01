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

    def test_vision_status_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis vision status"))
        self.assertEqual(plan.steps[0].agent_hint, "vision")
        self.assertEqual(plan.steps[0].metadata["operation"], "status")

    def test_camera_capture_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis inspect the camera"))
        self.assertEqual(plan.metadata["plan_type"], "vision")
        self.assertEqual(plan.steps[0].agent_hint, "vision")
        self.assertEqual(plan.steps[0].metadata["source"], "camera")

    def test_process_list_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis list running processes"))
        self.assertEqual(plan.metadata["plan_type"], "system")
        self.assertEqual(plan.steps[0].agent_hint, "system")
        self.assertEqual(plan.steps[0].metadata["action"], "list_processes")

    def test_process_terminate_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis stop process 2002"))
        self.assertEqual(plan.metadata["plan_type"], "workflow")
        self.assertEqual(plan.steps[0].agent_hint, "security")
        self.assertEqual(plan.steps[1].agent_hint, "system")
        self.assertEqual(plan.steps[1].metadata["action"], "terminate_process")
        self.assertEqual(plan.steps[1].metadata["pid"], 2002)

    def test_window_list_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis list open windows"))
        self.assertEqual(plan.metadata["plan_type"], "system")
        self.assertEqual(plan.steps[0].metadata["action"], "list_windows")

    def test_window_focus_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis focus window visual studio"))
        self.assertEqual(plan.metadata["plan_type"], "system")
        self.assertEqual(plan.steps[0].metadata["action"], "focus_window")
        self.assertEqual(plan.steps[0].metadata["title"], "visual studio")

    def test_desktop_status_plan_not_shadowed_by_vision(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis show desktop status"))
        self.assertEqual(plan.steps[0].agent_hint, "system")
        self.assertEqual(plan.steps[0].metadata["action"], "desktop_status")

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

    def test_compound_request_creates_workflow_dependencies(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis remember that my editor is VS Code then what did I say about editor"))
        self.assertEqual(plan.metadata["plan_type"], "workflow")
        self.assertGreaterEqual(len(plan.steps), 2)
        self.assertEqual(plan.steps[0].agent_hint, "memory")
        self.assertEqual(plan.steps[1].agent_hint, "memory")
        self.assertIn(plan.steps[0].step_id, plan.steps[1].depends_on)

    def test_suggestions_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis what should I do next"))
        self.assertEqual(plan.metadata["plan_type"], "proactive")
        self.assertEqual(plan.steps[0].agent_hint, "memory")
        self.assertEqual(plan.steps[0].metadata["operation"], "suggestions")

    def test_project_context_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis what are we working on"))
        self.assertEqual(plan.metadata["plan_type"], "project_context")
        self.assertEqual(plan.steps[0].agent_hint, "memory")
        self.assertEqual(plan.steps[0].metadata["operation"], "projects")

    def test_goal_create_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis track goal ship the API upgrade"))
        self.assertEqual(plan.metadata["plan_type"], "goals")
        self.assertEqual(plan.steps[0].agent_hint, "memory")
        self.assertEqual(plan.steps[0].metadata["operation"], "goal_create")
        self.assertEqual(plan.steps[0].metadata["title"], "ship the API upgrade")

    def test_focus_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis what should I focus on"))
        self.assertEqual(plan.metadata["plan_type"], "goals")
        self.assertEqual(plan.steps[0].metadata["operation"], "goals")
        self.assertEqual(plan.steps[0].metadata["status"], "active")

    def test_goal_complete_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis complete goal ship the API upgrade"))
        self.assertEqual(plan.metadata["plan_type"], "goals")
        self.assertEqual(plan.steps[0].metadata["operation"], "goal_update")
        self.assertEqual(plan.steps[0].metadata["status"], "completed")

    def test_workflow_create_plan(self) -> None:
        plan = self.planner.create_plan(
            CommandRequest(text="Jarvis create workflow research renewable energy then prepare a report then remind me tomorrow at 8am to review it")
        )
        self.assertEqual(plan.metadata["plan_type"], "workflows")
        self.assertEqual(plan.steps[0].metadata["operation"], "workflow_create")
        self.assertEqual(
            plan.steps[0].metadata["commands"],
            ["research renewable energy", "prepare a report", "remind me tomorrow at 8am to review it"],
        )

    def test_workflow_run_plan(self) -> None:
        plan = self.planner.create_plan(CommandRequest(text="Jarvis run workflow research renewable energy"))
        self.assertEqual(plan.metadata["plan_type"], "workflows")
        self.assertEqual(plan.steps[0].metadata["operation"], "workflow_run")
