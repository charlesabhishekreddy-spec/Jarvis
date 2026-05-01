from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from jarvis.core.models import CommandRequest, TaskPlan, TaskStep


WEEKLY_PATTERN = re.compile(
    r"every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+at\s+([0-2]?\d(?::[0-5]\d)?\s*(?:am|pm)?)",
    re.IGNORECASE,
)
DAILY_PATTERN = re.compile(r"every\s+day\s+at\s+([0-2]?\d(?::[0-5]\d)?\s*(?:am|pm)?)", re.IGNORECASE)
REMEMBER_PATTERN = re.compile(r"remember(?:\s+that)?\s+(.*)", re.IGNORECASE)
RECALL_PATTERN = re.compile(r"(?:recall|what do you know about|what did i say about)\s+(.*)", re.IGNORECASE)
SUGGESTIONS_PATTERN = re.compile(r"(?:what should i do next|what next|next steps?|any suggestions|what do you suggest)", re.IGNORECASE)
FOCUS_PATTERN = re.compile(r"(?:what should i focus on|top priorities|priority list|where should i focus)", re.IGNORECASE)
PROJECT_CONTEXT_PATTERN = re.compile(r"(?:project context|project summary|what are we working on|current project)", re.IGNORECASE)
GOAL_CREATE_PATTERN = re.compile(r"(?:track|create|add|start)\s+(?:a\s+)?goal(?:\s+to)?\s+(.+)", re.IGNORECASE)
GOAL_LIST_PATTERN = re.compile(r"(?:show|list)\s+(?:my\s+)?goals|what are my goals|active goals", re.IGNORECASE)
GOAL_REVIEW_PATTERN = re.compile(r"(?:refresh|reassess|review|update)\s+(?:my\s+)?goals", re.IGNORECASE)
GOAL_COMPLETE_PATTERN = re.compile(r"(?:complete|finish|close|mark done)\s+goal\s+(.+)", re.IGNORECASE)
GOAL_PAUSE_PATTERN = re.compile(r"(?:pause|hold)\s+goal\s+(.+)", re.IGNORECASE)
GOAL_RESUME_PATTERN = re.compile(r"(?:resume|reopen|reactivate)\s+goal\s+(.+)", re.IGNORECASE)
GOAL_BLOCK_PATTERN = re.compile(r"(?:block|mark blocked)\s+goal\s+(.+)", re.IGNORECASE)
WORKFLOW_CREATE_PATTERN = re.compile(r"(?:create|build|track)\s+(?:a\s+)?workflow(?:\s+(?:for|to))?\s+(.+)", re.IGNORECASE)
WORKFLOW_LIST_PATTERN = re.compile(r"(?:show|list)\s+workflows|what workflows are running|workflow status", re.IGNORECASE)
WORKFLOW_RUN_PATTERN = re.compile(r"(?:run|start|resume)\s+workflow\s+(.+)", re.IGNORECASE)
WORKFLOW_CANCEL_PATTERN = re.compile(r"(?:cancel|stop)\s+workflow\s+(.+)", re.IGNORECASE)
OPEN_PATTERN = re.compile(r"(?:open|launch)\s+(.+)", re.IGNORECASE)
WEATHER_PATTERN = re.compile(r"weather(?:\s+in)?\s+(.+)", re.IGNORECASE)
NEWS_PATTERN = re.compile(r"(?:news|latest)\s+(?:about\s+)?(.+)", re.IGNORECASE)
STATUS_PATTERN = re.compile(r"(?:status|health|resources)", re.IGNORECASE)
PROCESS_LIST_PATTERN = re.compile(
    r"(?:show|list|inspect)\s+(?:the\s+)?(?:running\s+)?(?:processes|apps|applications)|(?:what\s+is\s+running|running\s+process(?:es)?|running\s+apps)",
    re.IGNORECASE,
)
PROCESS_TERMINATE_PID_PATTERN = re.compile(
    r"(?:kill|stop|terminate|end|close)\s+(?:the\s+)?(?:process|pid|app(?:lication)?)\s+(\d+)",
    re.IGNORECASE,
)
PROCESS_TERMINATE_NAME_PATTERN = re.compile(
    r"(?:kill|stop|terminate|end|close)\s+(?:the\s+)?(?:process|app(?:lication)?)\s+(.+)",
    re.IGNORECASE,
)
WINDOW_LIST_PATTERN = re.compile(
    r"(?:show|list|inspect)\s+(?:the\s+)?(?:open|active)?\s*windows|(?:window list|open windows|active windows)",
    re.IGNORECASE,
)
WINDOW_FOCUS_PATTERN = re.compile(
    r"(?:focus|activate|switch to|bring to front)\s+(?:the\s+)?window\s+(.+)",
    re.IGNORECASE,
)
WINDOW_MINIMIZE_PATTERN = re.compile(
    r"(?:minimi[sz]e|hide)\s+(?:the\s+)?window\s+(.+)",
    re.IGNORECASE,
)
WINDOW_MAXIMIZE_PATTERN = re.compile(
    r"(?:maximi[sz]e|fullscreen)\s+(?:the\s+)?window\s+(.+)",
    re.IGNORECASE,
)
VISION_STATUS_PATTERN = re.compile(
    r"(?:vision status|camera status|ocr status|screen capture status|what can you see)",
    re.IGNORECASE,
)
SCREEN_CAPTURE_PATTERN = re.compile(
    r"(?:inspect|capture|scan|read|analy[sz]e).*(?:screen|display|desktop)|(?:read|ocr).*(?:screen|display)",
    re.IGNORECASE,
)
CAMERA_CAPTURE_PATTERN = re.compile(
    r"(?:inspect|capture|scan|check|analy[sz]e|show).*(?:camera|webcam)|(?:take|grab).*(?:photo|picture).*(?:camera|webcam)?",
    re.IGNORECASE,
)
TOOLS_PATTERN = re.compile(r"(?:tools|capabilities|what can you do)", re.IGNORECASE)
STARTUP_STATUS_PATTERN = re.compile(
    r"(?:startup status|autostart status|boot status|start(?:ing)? on (?:boot|login)|is jarvis set to start)",
    re.IGNORECASE,
)
STARTUP_INSTALL_PATTERN = re.compile(
    r"(?:enable|install|configure|register|set up).*(?:startup|autostart|start on (?:boot|login))",
    re.IGNORECASE,
)
STARTUP_UNINSTALL_PATTERN = re.compile(
    r"(?:disable|remove|uninstall|delete).*(?:startup|autostart|start on (?:boot|login))",
    re.IGNORECASE,
)
DESKTOP_STATUS_PATTERN = re.compile(r"(?:desktop status|screen size|automation status|mouse status)", re.IGNORECASE)
MOUSE_MOVE_PATTERN = re.compile(
    r"(?:move (?:the )?(?:mouse|cursor)\s+to)\s+(-?\d+)\s*(?:,|\s)\s*(-?\d+)",
    re.IGNORECASE,
)
MOUSE_CLICK_PATTERN = re.compile(
    r"(?:(double click|right click|middle click|click))(?:\s+at)?\s+(-?\d+)\s*(?:,|\s)\s*(-?\d+)",
    re.IGNORECASE,
)
KEYBOARD_TYPE_PATTERN = re.compile(r"(?:type|enter)\s+(.+)", re.IGNORECASE)
KEYBOARD_PRESS_PATTERN = re.compile(r"(?:press|hit|shortcut|hotkey)\s+(.+)", re.IGNORECASE)
WORKFLOW_SPLIT_PATTERN = re.compile(r"\b(?:and then|then|after that|followed by|next)\b", re.IGNORECASE)


class TaskPlanner:
    def __init__(self, workspace_root: str | None = None, startup_mode: str = "api") -> None:
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
        self.startup_mode = startup_mode

    def create_plan(self, request: CommandRequest) -> TaskPlan:
        text = self._normalize(request.text)
        steps, metadata = self._build_steps(text)
        return TaskPlan(goal=text, steps=steps, metadata=metadata)

    def _normalize(self, text: str) -> str:
        lowered = text.strip()
        return re.sub(r"^(hey\s+jarvis|jarvis)[,\s:]+", "", lowered, flags=re.IGNORECASE)

    def _build_steps(self, text: str, allow_compound: bool = True) -> tuple[list[TaskStep], dict[str, str]]:
        if allow_compound:
            workflow_create_match = WORKFLOW_CREATE_PATTERN.search(text)
            if workflow_create_match:
                commands = self._extract_workflow_commands(workflow_create_match.group(1).strip())
                return [
                    TaskStep(
                        title="Create persistent workflow",
                        description=text,
                        agent_hint="automation",
                        metadata={
                            "operation": "workflow_create",
                            "title": self._workflow_title_from_commands(commands),
                            "commands": commands,
                        },
                    )
                ], {"plan_type": "workflows"}
        if WORKFLOW_LIST_PATTERN.search(text):
            return [
                TaskStep(
                    title="List workflows",
                    description=text,
                    agent_hint="automation",
                    metadata={"operation": "workflows", "limit": 10},
                )
            ], {"plan_type": "workflows"}

        workflow_run_match = WORKFLOW_RUN_PATTERN.search(text)
        if workflow_run_match:
            return [
                TaskStep(
                    title="Run workflow",
                    description=text,
                    agent_hint="automation",
                    metadata={"operation": "workflow_run", "title": workflow_run_match.group(1).strip().rstrip(".")},
                )
            ], {"plan_type": "workflows"}

        workflow_cancel_match = WORKFLOW_CANCEL_PATTERN.search(text)
        if workflow_cancel_match:
            return [
                TaskStep(
                    title="Cancel workflow",
                    description=text,
                    agent_hint="automation",
                    metadata={"operation": "workflow_cancel", "title": workflow_cancel_match.group(1).strip().rstrip(".")},
                )
            ], {"plan_type": "workflows"}

        if allow_compound:
            workflow_steps = self._build_workflow_steps(text)
            if workflow_steps:
                return workflow_steps, {"plan_type": "workflow"}

        remember_match = REMEMBER_PATTERN.search(text)
        if remember_match:
            return [
                TaskStep(
                    title="Store memory",
                    description=remember_match.group(1),
                    agent_hint="memory",
                    metadata={"operation": "remember", "content": remember_match.group(1), "category": "user_preference"},
                )
            ], {"plan_type": "memory"}

        recall_match = RECALL_PATTERN.search(text)
        if recall_match:
            return [
                TaskStep(
                    title="Recall memory",
                    description=recall_match.group(1),
                    agent_hint="memory",
                    metadata={"operation": "recall", "query": recall_match.group(1)},
                )
            ], {"plan_type": "memory"}

        if SUGGESTIONS_PATTERN.search(text):
            return [
                TaskStep(
                    title="Review proactive suggestions",
                    description=text,
                    agent_hint="memory",
                    metadata={"operation": "suggestions", "limit": 5},
                )
            ], {"plan_type": "proactive"}

        if FOCUS_PATTERN.search(text):
            return [
                TaskStep(
                    title="Review active goals",
                    description=text,
                    agent_hint="memory",
                    metadata={"operation": "goals", "status": "active", "limit": 5},
                )
            ], {"plan_type": "goals"}

        if PROJECT_CONTEXT_PATTERN.search(text):
            return [
                TaskStep(
                    title="Review project context",
                    description=text,
                    agent_hint="memory",
                    metadata={"operation": "projects", "limit": 5},
                )
            ], {"plan_type": "project_context"}

        goal_create_match = GOAL_CREATE_PATTERN.search(text)
        if goal_create_match:
            title = goal_create_match.group(1).strip().rstrip(".")
            return [
                TaskStep(
                    title="Track persistent goal",
                    description=text,
                    agent_hint="memory",
                    metadata={
                        "operation": "goal_create",
                        "title": title,
                        "detail": title,
                        "priority": self._extract_goal_priority(text),
                    },
                )
            ], {"plan_type": "goals"}

        if GOAL_LIST_PATTERN.search(text):
            return [
                TaskStep(
                    title="List persistent goals",
                    description=text,
                    agent_hint="memory",
                    metadata={"operation": "goals", "status": "active", "limit": 10},
                )
            ], {"plan_type": "goals"}

        if GOAL_REVIEW_PATTERN.search(text):
            return [
                TaskStep(
                    title="Review active goals",
                    description=text,
                    agent_hint="memory",
                    metadata={"operation": "review_goals"},
                )
            ], {"plan_type": "goals"}

        goal_complete_match = GOAL_COMPLETE_PATTERN.search(text)
        if goal_complete_match:
            return [
                TaskStep(
                    title="Complete persistent goal",
                    description=text,
                    agent_hint="memory",
                    metadata={
                        "operation": "goal_update",
                        "title": goal_complete_match.group(1).strip().rstrip("."),
                        "statuses": ["active", "paused", "blocked", "completed"],
                        "status": "completed",
                    },
                )
            ], {"plan_type": "goals"}

        goal_pause_match = GOAL_PAUSE_PATTERN.search(text)
        if goal_pause_match:
            return [
                TaskStep(
                    title="Pause persistent goal",
                    description=text,
                    agent_hint="memory",
                    metadata={
                        "operation": "goal_update",
                        "title": goal_pause_match.group(1).strip().rstrip("."),
                        "statuses": ["active", "blocked", "paused"],
                        "status": "paused",
                    },
                )
            ], {"plan_type": "goals"}

        goal_resume_match = GOAL_RESUME_PATTERN.search(text)
        if goal_resume_match:
            return [
                TaskStep(
                    title="Resume persistent goal",
                    description=text,
                    agent_hint="memory",
                    metadata={
                        "operation": "goal_update",
                        "title": goal_resume_match.group(1).strip().rstrip("."),
                        "statuses": ["paused", "blocked", "active"],
                        "status": "active",
                    },
                )
            ], {"plan_type": "goals"}

        goal_block_match = GOAL_BLOCK_PATTERN.search(text)
        if goal_block_match:
            return [
                TaskStep(
                    title="Block persistent goal",
                    description=text,
                    agent_hint="memory",
                    metadata={
                        "operation": "goal_update",
                        "title": goal_block_match.group(1).strip().rstrip("."),
                        "statuses": ["active", "paused", "blocked"],
                        "status": "blocked",
                    },
                )
            ], {"plan_type": "goals"}

        daily_match = DAILY_PATTERN.search(text)
        if daily_match:
            return [
                TaskStep(
                    title="Schedule daily reminder",
                    description=text,
                    agent_hint="automation",
                    metadata={
                        "schedule_type": "daily",
                        "message": text,
                        "time_of_day": self._normalize_time(daily_match.group(1)),
                    },
                )
            ], {"plan_type": "automation"}

        weekly_match = WEEKLY_PATTERN.search(text)
        if weekly_match:
            return [
                TaskStep(
                    title="Schedule weekly reminder",
                    description=text,
                    agent_hint="automation",
                    metadata={
                        "schedule_type": "weekly",
                        "message": text,
                        "day_name": weekly_match.group(1),
                        "time_of_day": self._normalize_time(weekly_match.group(2)),
                    },
                )
            ], {"plan_type": "automation"}

        if text.lower().startswith("remind me"):
            return [
                TaskStep(
                    title="Schedule reminder",
                    description=text,
                    agent_hint="automation",
                    metadata={"schedule_type": "once", "message": text, "run_at": self._extract_iso_datetime(text)},
                )
            ], {"plan_type": "automation"}

        weather_match = WEATHER_PATTERN.search(text)
        if weather_match:
            return [
                TaskStep(
                    title="Lookup weather",
                    description=text,
                    agent_hint="research",
                    metadata={"query_type": "weather", "location": weather_match.group(1).strip()},
                )
            ], {"plan_type": "research"}

        news_match = NEWS_PATTERN.search(text)
        if "news" in text.lower() or "latest" in text.lower():
            topic = news_match.group(1).strip() if news_match else text
            return [
                TaskStep(
                    title="Get latest news",
                    description=text,
                    agent_hint="research",
                    metadata={"query_type": "news", "topic": topic},
                )
            ], {"plan_type": "research"}

        if PROCESS_LIST_PATTERN.search(text):
            return [
                TaskStep(
                    title="List running processes",
                    description=text,
                    agent_hint="system",
                    metadata={"action": "list_processes", "limit": 20},
                )
            ], {"plan_type": "system"}

        process_terminate_pid_match = PROCESS_TERMINATE_PID_PATTERN.search(text)
        if process_terminate_pid_match:
            pid = int(process_terminate_pid_match.group(1))
            steps = [
                TaskStep(
                    title="Evaluate process termination safety",
                    description=text,
                    agent_hint="security",
                    metadata={"command": text},
                ),
                TaskStep(
                    title="Terminate process",
                    description=text,
                    agent_hint="system",
                    metadata={
                        "action": "terminate_process",
                        "pid": pid,
                        "requires_confirmation": True,
                        "risk_level": "high",
                    },
                ),
            ]
            return self._chain_steps(steps), {"plan_type": "workflow"}

        process_terminate_name_match = PROCESS_TERMINATE_NAME_PATTERN.search(text)
        if process_terminate_name_match:
            target_name = process_terminate_name_match.group(1).strip().rstrip(".")
            steps = [
                TaskStep(
                    title="Evaluate process termination safety",
                    description=text,
                    agent_hint="security",
                    metadata={"command": text},
                ),
                TaskStep(
                    title="Terminate process",
                    description=text,
                    agent_hint="system",
                    metadata={
                        "action": "terminate_process",
                        "process_name": target_name,
                        "requires_confirmation": True,
                        "risk_level": "high",
                    },
                ),
            ]
            return self._chain_steps(steps), {"plan_type": "workflow"}

        if WINDOW_LIST_PATTERN.search(text):
            return [
                TaskStep(
                    title="List desktop windows",
                    description=text,
                    agent_hint="system",
                    metadata={"action": "list_windows", "limit": 20},
                )
            ], {"plan_type": "system"}

        window_focus_match = WINDOW_FOCUS_PATTERN.search(text)
        if window_focus_match:
            return [
                TaskStep(
                    title="Focus desktop window",
                    description=text,
                    agent_hint="system",
                    metadata={"action": "focus_window", "title": window_focus_match.group(1).strip().rstrip(".")},
                )
            ], {"plan_type": "system"}

        window_minimize_match = WINDOW_MINIMIZE_PATTERN.search(text)
        if window_minimize_match:
            return [
                TaskStep(
                    title="Minimize desktop window",
                    description=text,
                    agent_hint="system",
                    metadata={"action": "minimize_window", "title": window_minimize_match.group(1).strip().rstrip(".")},
                )
            ], {"plan_type": "system"}

        window_maximize_match = WINDOW_MAXIMIZE_PATTERN.search(text)
        if window_maximize_match:
            return [
                TaskStep(
                    title="Maximize desktop window",
                    description=text,
                    agent_hint="system",
                    metadata={"action": "maximize_window", "title": window_maximize_match.group(1).strip().rstrip(".")},
                )
            ], {"plan_type": "system"}

        if VISION_STATUS_PATTERN.search(text):
            return [
                TaskStep(
                    title="Inspect vision runtime status",
                    description=text,
                    agent_hint="vision",
                    metadata={"operation": "status"},
                )
            ], {"plan_type": "vision"}

        if CAMERA_CAPTURE_PATTERN.search(text):
            return [
                TaskStep(
                    title="Inspect camera",
                    description=text,
                    agent_hint="vision",
                    metadata={
                        "operation": "inspect",
                        "source": "camera",
                        "save_artifact": True,
                        "include_ocr": "read" in text.lower() or "ocr" in text.lower(),
                    },
                )
            ], {"plan_type": "vision"}

        if (
            SCREEN_CAPTURE_PATTERN.search(text)
            or ("screen" in text.lower() and not DESKTOP_STATUS_PATTERN.search(text))
            or "ocr" in text.lower()
        ):
            return [
                TaskStep(
                    title="Inspect screen",
                    description=text,
                    agent_hint="vision",
                    metadata={
                        "operation": "inspect",
                        "source": "screen",
                        "save_artifact": True,
                        "include_ocr": True,
                    },
                )
            ], {"plan_type": "vision"}

        if DESKTOP_STATUS_PATTERN.search(text):
            return [
                TaskStep(
                    title="Inspect desktop automation status",
                    description=text,
                    agent_hint="system",
                    metadata={"action": "desktop_status"},
                )
            ], {"plan_type": "system"}

        mouse_move_match = MOUSE_MOVE_PATTERN.search(text)
        if mouse_move_match:
            steps = [
                TaskStep(
                    title="Evaluate mouse automation safety",
                    description=text,
                    agent_hint="security",
                    metadata={"command": text},
                ),
                TaskStep(
                    title="Move mouse cursor",
                    description=text,
                    agent_hint="system",
                    metadata={
                        "action": "mouse_move",
                        "x": int(mouse_move_match.group(1)),
                        "y": int(mouse_move_match.group(2)),
                        "duration": 0.0,
                        "requires_confirmation": True,
                        "risk_level": "high",
                    },
                ),
            ]
            return self._chain_steps(steps), {"plan_type": "workflow"}

        mouse_click_match = MOUSE_CLICK_PATTERN.search(text)
        if mouse_click_match:
            button_token = mouse_click_match.group(1).lower()
            button = "right" if "right" in button_token else "middle" if "middle" in button_token else "left"
            clicks = 2 if "double" in button_token else 1
            steps = [
                TaskStep(
                    title="Evaluate mouse click safety",
                    description=text,
                    agent_hint="security",
                    metadata={"command": text},
                ),
                TaskStep(
                    title="Click mouse",
                    description=text,
                    agent_hint="system",
                    metadata={
                        "action": "mouse_click",
                        "x": int(mouse_click_match.group(2)),
                        "y": int(mouse_click_match.group(3)),
                        "button": button,
                        "clicks": clicks,
                        "requires_confirmation": True,
                        "risk_level": "high",
                    },
                ),
            ]
            return self._chain_steps(steps), {"plan_type": "workflow"}

        keyboard_press_match = KEYBOARD_PRESS_PATTERN.search(text)
        if keyboard_press_match:
            keys = self._extract_keys(keyboard_press_match.group(1))
            steps = [
                TaskStep(
                    title="Evaluate keyboard automation safety",
                    description=text,
                    agent_hint="security",
                    metadata={"command": text},
                ),
                TaskStep(
                    title="Press keyboard keys",
                    description=text,
                    agent_hint="system",
                    metadata={
                        "action": "keyboard_press",
                        "keys": keys,
                        "requires_confirmation": True,
                        "risk_level": "high",
                    },
                ),
            ]
            return self._chain_steps(steps), {"plan_type": "workflow"}

        keyboard_type_match = KEYBOARD_TYPE_PATTERN.search(text)
        if keyboard_type_match:
            steps = [
                TaskStep(
                    title="Evaluate typing safety",
                    description=text,
                    agent_hint="security",
                    metadata={"command": text},
                ),
                TaskStep(
                    title="Type text",
                    description=text,
                    agent_hint="system",
                    metadata={
                        "action": "keyboard_type",
                        "text": keyboard_type_match.group(1).strip(),
                        "interval": 0.0,
                        "requires_confirmation": True,
                        "risk_level": "high",
                    },
                ),
            ]
            return self._chain_steps(steps), {"plan_type": "workflow"}

        if STARTUP_STATUS_PATTERN.search(text):
            return [
                TaskStep(
                    title="Inspect startup registration",
                    description=text,
                    agent_hint="system",
                    metadata={"action": "startup_status", "mode": self._extract_startup_mode(text)},
                )
            ], {"plan_type": "system"}

        if STARTUP_INSTALL_PATTERN.search(text):
            mode = self._extract_startup_mode(text)
            steps = [
                TaskStep(
                    title="Evaluate startup configuration safety",
                    description=text,
                    agent_hint="security",
                    metadata={"command": text},
                ),
                TaskStep(
                    title="Install startup registration",
                    description=text,
                    agent_hint="system",
                    metadata={"action": "install_startup", "mode": mode, "requires_confirmation": True, "risk_level": "high"},
                ),
            ]
            return self._chain_steps(steps), {"plan_type": "workflow"}

        if STARTUP_UNINSTALL_PATTERN.search(text):
            steps = [
                TaskStep(
                    title="Evaluate startup removal safety",
                    description=text,
                    agent_hint="security",
                    metadata={"command": text},
                ),
                TaskStep(
                    title="Remove startup registration",
                    description=text,
                    agent_hint="system",
                    metadata={"action": "uninstall_startup", "requires_confirmation": True, "risk_level": "high"},
                ),
            ]
            return self._chain_steps(steps), {"plan_type": "workflow"}

        if STATUS_PATTERN.search(text):
            return [
                TaskStep(
                    title="Inspect system status",
                    description=text,
                    agent_hint="system",
                    metadata={"action": "resource_usage"},
                )
            ], {"plan_type": "system"}

        if TOOLS_PATTERN.search(text):
            return [
                TaskStep(
                    title="Describe available tools",
                    description=text,
                    agent_hint="commander",
                    metadata={"include_tools": True},
                )
            ], {"plan_type": "commander"}

        open_match = OPEN_PATTERN.search(text)
        if open_match:
            target = open_match.group(1).strip()
            candidate = Path(target)
            action = "open_path" if candidate.exists() else "launch_application"
            metadata = {"action": action}
            if action == "open_path":
                metadata["path"] = str(candidate)
            else:
                metadata["application"] = target
            return [TaskStep(title="Open target", description=text, agent_hint="system", metadata=metadata)], {"plan_type": "system"}

        if self._contains_any_term(text, ("report", "research", "prepare")):
            slug = self._slugify(text)[:50]
            output_path = self.workspace_root / "reports" / f"{slug or uuid4().hex}.md"
            steps = [
                TaskStep(
                    title="Research topic",
                    description=text,
                    agent_hint="research",
                    metadata={"query": text},
                ),
                TaskStep(
                    title="Compose report",
                    description="Summarize findings into a structured note.",
                    agent_hint="commander",
                    metadata={"write_report": True},
                ),
                TaskStep(
                    title="Save report",
                    description=f"Write the report to {output_path}",
                    agent_hint="system",
                    metadata={"action": "write_file", "path": str(output_path), "content_from_previous": True},
                ),
                TaskStep(
                    title="Validate deliverable",
                    description="Confirm the report exists and summarize what was produced.",
                    agent_hint="commander",
                    metadata={"validate_deliverable": True},
                ),
            ]
            return self._chain_steps(steps), {"plan_type": "workflow"}

        if self._contains_any_term(text, ("run", "execute", "terminal")):
            steps = [
                TaskStep(
                    title="Evaluate execution safety",
                    description=text,
                    agent_hint="security",
                    metadata={"command": self._extract_shell_command(text)},
                ),
                TaskStep(
                    title="Run command",
                    description=text,
                    agent_hint="system",
                    metadata={
                        "action": "shell",
                        "command": self._extract_shell_command(text),
                        "requires_confirmation": True,
                        "risk_level": "high",
                    },
                ),
            ]
            return self._chain_steps(steps), {"plan_type": "workflow"}

        return [
            TaskStep(
                title="Autonomous request handling",
                description=text,
                agent_hint="autonomous",
            )
        ], {"plan_type": "autonomous"}

    def _build_workflow_steps(self, text: str) -> list[TaskStep]:
        parts = [part.strip(" ,.") for part in WORKFLOW_SPLIT_PATTERN.split(text) if part.strip(" ,.")]
        if len(parts) < 2:
            return []
        steps: list[TaskStep] = []
        previous_step_id: str | None = None
        for index, part in enumerate(parts, start=1):
            clause_steps, _ = self._build_steps(part, allow_compound=False)
            if not clause_steps:
                continue
            for clause_index, step in enumerate(clause_steps):
                if clause_index == 0 and previous_step_id:
                    step.depends_on.append(previous_step_id)
                steps.append(step)
                previous_step_id = step.step_id
            if clause_steps:
                clause_steps[0].title = f"Workflow {index}: {clause_steps[0].title}"
        return steps

    def _chain_steps(self, steps: list[TaskStep]) -> list[TaskStep]:
        previous_step_id: str | None = None
        for step in steps:
            if previous_step_id and previous_step_id not in step.depends_on:
                step.depends_on.append(previous_step_id)
            previous_step_id = step.step_id
        return steps

    def _normalize_time(self, raw: str) -> str:
        value = raw.strip().lower()
        formats = ("%H:%M:%S", "%H:%M", "%I%p", "%I:%M%p", "%I %p", "%I:%M %p")
        normalized = value.replace(" ", "")
        for fmt in formats:
            try:
                return datetime.strptime(normalized, fmt).strftime("%H:%M:%S")
            except ValueError:
                continue
        raise ValueError(f"Unsupported time format: {raw}")

    def _extract_iso_datetime(self, text: str) -> str | None:
        iso_match = re.search(r"\d{4}-\d{2}-\d{2}[tT ]\d{2}:\d{2}(?::\d{2})?", text)
        if iso_match:
            return iso_match.group(0).replace(" ", "T")
        tomorrow_match = re.search(r"tomorrow\s+at\s+([0-2]?\d(?::[0-5]\d)?\s*(?:am|pm)?)", text, re.IGNORECASE)
        if tomorrow_match:
            target = datetime.now(timezone.utc) + timedelta(days=1)
            hour, minute, second = [int(part) for part in self._normalize_time(tomorrow_match.group(1)).split(":")]
            return target.replace(hour=hour, minute=minute, second=second, microsecond=0).isoformat()
        relative_match = re.search(r"in\s+(\d+)\s+(minute|minutes|hour|hours|day|days)", text, re.IGNORECASE)
        if relative_match:
            count = int(relative_match.group(1))
            unit = relative_match.group(2).lower()
            if "hour" in unit:
                delta = timedelta(hours=count)
            elif "day" in unit:
                delta = timedelta(days=count)
            else:
                delta = timedelta(minutes=count)
            return (datetime.now(timezone.utc) + delta).replace(microsecond=0).isoformat()
        at_match = re.search(r"\bat\s+([0-2]?\d(?::[0-5]\d)?\s*(?:am|pm)?)", text, re.IGNORECASE)
        if at_match:
            now = datetime.now(timezone.utc)
            hour, minute, second = [int(part) for part in self._normalize_time(at_match.group(1)).split(":")]
            target = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target.isoformat()
        return None

    def _slugify(self, text: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")

    def _contains_any_term(self, text: str, terms: tuple[str, ...]) -> bool:
        lowered = text.lower()
        for term in terms:
            if " " in term:
                if term in lowered:
                    return True
                continue
            if re.search(rf"\b{re.escape(term)}\b", lowered):
                return True
        return False

    def _extract_shell_command(self, text: str) -> str:
        match = re.match(r"^(?:run|execute)\s+(.+)$", text.strip(), re.IGNORECASE)
        if match:
            return match.group(1).strip()
        terminal_match = re.match(r"^(?:terminal(?:\s+command)?)\s+(.+)$", text.strip(), re.IGNORECASE)
        if terminal_match:
            return terminal_match.group(1).strip()
        return text.strip()

    def _extract_startup_mode(self, text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ("background", "headless", "daemon")):
            return "background"
        if any(token in lowered for token in ("api", "dashboard", "web")):
            return "api"
        return self.startup_mode

    def _extract_keys(self, raw: str) -> list[str]:
        cleaned = raw.strip().strip(".")
        if "+" in cleaned:
            parts = cleaned.split("+")
        else:
            parts = re.split(r"(?:\s*,\s*|\s+)", cleaned)
        aliases = {
            "control": "ctrl",
            "return": "enter",
            "escape": "esc",
            "windows": "win",
        }
        normalized = [aliases.get(part.lower(), part.lower()) for part in parts if part]
        return normalized

    def _extract_goal_priority(self, text: str) -> int:
        lowered = text.lower()
        if any(token in lowered for token in ("critical", "urgent")):
            return 95
        if "high priority" in lowered or "important" in lowered:
            return 80
        if "low priority" in lowered:
            return 30
        return 60

    def _extract_workflow_commands(self, text: str) -> list[str]:
        commands = [part.strip(" ,.") for part in WORKFLOW_SPLIT_PATTERN.split(text) if part.strip(" ,.")]
        return commands or [text.strip()]

    def _workflow_title_from_commands(self, commands: list[str]) -> str:
        if not commands:
            return "Workflow"
        if len(commands) == 1:
            return commands[0]
        return f"{commands[0]} and {len(commands) - 1} more steps"
