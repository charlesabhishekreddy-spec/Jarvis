from __future__ import annotations

import argparse
import json
import sys

import requests

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import (
        QApplication,
        QLabel,
        QMainWindow,
        QPushButton,
        QPlainTextEdit,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyQt6 is not installed. Install requirements-optional.txt to run the dashboard.") from exc


class JarvisDashboard(QMainWindow):
    def __init__(self, api_base: str, poll_seconds: int = 3) -> None:
        super().__init__()
        self.api_base = api_base.rstrip("/")
        self.setWindowTitle("JARVIS Control Dashboard")
        self.resize(1200, 800)

        container = QWidget()
        layout = QVBoxLayout(container)
        self.status_label = QLabel("Connecting to JARVIS...")
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        layout.addWidget(self.status_label)
        layout.addWidget(self.refresh_button)

        tabs = QTabWidget()
        self.status_view = QPlainTextEdit()
        self.status_view.setReadOnly(True)
        self.activities_view = QPlainTextEdit()
        self.activities_view.setReadOnly(True)
        self.tasks_view = QPlainTextEdit()
        self.tasks_view.setReadOnly(True)
        self.commands_view = QPlainTextEdit()
        self.commands_view.setReadOnly(True)
        tabs.addTab(self.status_view, "Status")
        tabs.addTab(self.activities_view, "Activity")
        tabs.addTab(self.tasks_view, "Tasks")
        tabs.addTab(self.commands_view, "Commands")
        layout.addWidget(tabs)
        self.setCentralWidget(container)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(max(poll_seconds, 1) * 1000)
        self.refresh()

    def refresh(self) -> None:
        try:
            response = requests.get(f"{self.api_base}/status", timeout=5)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # pragma: no cover
            self.status_label.setText(f"JARVIS unavailable: {exc}")
            return

        self.status_label.setText("JARVIS connected")
        self.status_view.setPlainText(json.dumps(payload["status"], indent=2))
        self.activities_view.setPlainText(json.dumps(payload["activities"], indent=2))
        self.tasks_view.setPlainText(json.dumps(payload["tasks"], indent=2))
        self.commands_view.setPlainText(json.dumps(payload["conversations"], indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the JARVIS desktop dashboard.")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--poll-seconds", type=int, default=3)
    args = parser.parse_args()

    app = QApplication(sys.argv)
    dashboard = JarvisDashboard(api_base=args.api, poll_seconds=args.poll_seconds)
    dashboard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
