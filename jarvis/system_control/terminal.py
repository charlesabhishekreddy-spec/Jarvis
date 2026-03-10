from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from jarvis.security.manager import SecurityManager


@dataclass(slots=True)
class ShellCommandResult:
    returncode: int
    stdout: str
    stderr: str


class TerminalExecutor:
    def __init__(self, security: SecurityManager) -> None:
        self.security = security

    def run(self, command: str, workdir: str | None = None, timeout: int = 60) -> ShellCommandResult:
        if not self.security.settings.allow_shell:
            return ShellCommandResult(returncode=1, stdout="", stderr="Shell execution is disabled by policy.")
        if workdir and not self.security.is_path_allowed(workdir):
            return ShellCommandResult(returncode=1, stdout="", stderr=f"Blocked workdir: {workdir}")
        cwd = str(Path(workdir).resolve()) if workdir else None
        args = shlex.split(command, posix=False)
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return ShellCommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
        )
