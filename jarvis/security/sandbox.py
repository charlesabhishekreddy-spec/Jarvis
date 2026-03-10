from __future__ import annotations

from pathlib import Path


class SandboxPolicy:
    def __init__(self, allowed_workdirs: list[str]) -> None:
        self.allowed_workdirs = [Path(path).resolve() for path in allowed_workdirs]

    def is_path_allowed(self, path: str) -> bool:
        candidate = Path(path).resolve()
        return any(str(candidate).startswith(str(allowed)) for allowed in self.allowed_workdirs)
