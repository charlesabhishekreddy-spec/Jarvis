from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv() -> None:
        return None


@dataclass(slots=True)
class RuntimeSettings:
    env: str = "development"
    data_dir: str = ".jarvis_runtime"
    host: str = "127.0.0.1"
    port: int = 8000
    auto_start_api: bool = True


@dataclass(slots=True)
class VoiceSettings:
    enabled: bool = True
    wake_word: str = "hey jarvis"
    language: str = "en"
    use_porcupine: bool = False
    streaming: bool = False


@dataclass(slots=True)
class MemorySettings:
    sqlite_path: str = ".jarvis_runtime/jarvis.db"
    semantic_index_path: str = ".jarvis_runtime/semantic_memory.json"
    max_recent_items: int = 200


@dataclass(slots=True)
class SecuritySettings:
    confirm_dangerous_commands: bool = True
    allow_shell: bool = True
    allowed_workdirs: list[str] = field(default_factory=lambda: ["./"])


@dataclass(slots=True)
class APIKeys:
    news_api_key: str = ""
    weather_api_key: str = ""
    elevenlabs_api_key: str = ""


@dataclass(slots=True)
class IntelligenceSettings:
    provider: str = "heuristic"
    model: str = "local-heuristic"
    endpoint: str = "http://127.0.0.1:11434/api/generate"
    timeout_seconds: int = 20


@dataclass(slots=True)
class StartupSettings:
    task_name: str = "JARVIS"
    default_mode: str = "api"


@dataclass(slots=True)
class LearningSettings:
    enabled: bool = True
    auto_extract_preferences: bool = True
    max_patterns: int = 500


@dataclass(slots=True)
class UISettings:
    dashboard_poll_seconds: int = 3


@dataclass(slots=True)
class Settings:
    runtime: RuntimeSettings = field(default_factory=RuntimeSettings)
    voice: VoiceSettings = field(default_factory=VoiceSettings)
    memory: MemorySettings = field(default_factory=MemorySettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    api_keys: APIKeys = field(default_factory=APIKeys)
    intelligence: IntelligenceSettings = field(default_factory=IntelligenceSettings)
    startup: StartupSettings = field(default_factory=StartupSettings)
    learning: LearningSettings = field(default_factory=LearningSettings)
    ui: UISettings = field(default_factory=UISettings)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _deep_update(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_update(merged[key], value)
        else:
            merged[key] = value
    return merged


def _as_settings(data: dict[str, Any]) -> Settings:
    return Settings(
        runtime=RuntimeSettings(**data.get("runtime", {})),
        voice=VoiceSettings(**data.get("voice", {})),
        memory=MemorySettings(**data.get("memory", {})),
        security=SecuritySettings(**data.get("security", {})),
        api_keys=APIKeys(**data.get("api_keys", {})),
        intelligence=IntelligenceSettings(**data.get("intelligence", {})),
        startup=StartupSettings(**data.get("startup", {})),
        learning=LearningSettings(**data.get("learning", {})),
        ui=UISettings(**data.get("ui", {})),
    )


def resolve_data_path(path: str, root: Path) -> str:
    candidate = Path(path)
    return str(candidate if candidate.is_absolute() else (root / candidate).resolve())


def load_settings(path: str | None = None) -> Settings:
    load_dotenv()
    package_root = Path(__file__).resolve().parents[1]
    config_path = Path(path) if path else package_root / "config" / "settings.yaml"
    raw: dict[str, Any] = {}
    if yaml is not None and config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    data = _deep_update(Settings().to_dict(), raw)
    data["runtime"]["env"] = os.getenv("JARVIS_ENV", data["runtime"]["env"])
    data["runtime"]["host"] = os.getenv("JARVIS_HOST", data["runtime"]["host"])
    data["runtime"]["port"] = int(os.getenv("JARVIS_PORT", data["runtime"]["port"]))
    data["security"]["confirm_dangerous_commands"] = (
        os.getenv("JARVIS_CONFIRM_DANGEROUS", str(data["security"]["confirm_dangerous_commands"])).lower()
        == "true"
    )
    data["security"]["allow_shell"] = os.getenv("JARVIS_ALLOW_SHELL", str(data["security"]["allow_shell"])).lower() == "true"
    data["api_keys"]["news_api_key"] = os.getenv("JARVIS_NEWS_API_KEY", data["api_keys"]["news_api_key"])
    data["api_keys"]["weather_api_key"] = os.getenv("JARVIS_WEATHER_API_KEY", data["api_keys"]["weather_api_key"])
    data["api_keys"]["elevenlabs_api_key"] = os.getenv(
        "JARVIS_ELEVENLABS_API_KEY", data["api_keys"]["elevenlabs_api_key"]
    )
    data["intelligence"]["provider"] = os.getenv("JARVIS_INTELLIGENCE_PROVIDER", data["intelligence"]["provider"])
    data["intelligence"]["model"] = os.getenv("JARVIS_INTELLIGENCE_MODEL", data["intelligence"]["model"])
    data["intelligence"]["endpoint"] = os.getenv("JARVIS_INTELLIGENCE_ENDPOINT", data["intelligence"]["endpoint"])
    data["startup"]["task_name"] = os.getenv("JARVIS_STARTUP_TASK_NAME", data["startup"]["task_name"])
    data["startup"]["default_mode"] = os.getenv("JARVIS_STARTUP_MODE", data["startup"]["default_mode"])
    data["learning"]["enabled"] = os.getenv("JARVIS_LEARNING_ENABLED", str(data["learning"]["enabled"])).lower() == "true"
    settings = _as_settings(data)
    root = package_root.parent
    settings.runtime.data_dir = resolve_data_path(settings.runtime.data_dir, root)
    settings.memory.sqlite_path = resolve_data_path(settings.memory.sqlite_path, root)
    settings.memory.semantic_index_path = resolve_data_path(settings.memory.semantic_index_path, root)
    settings.security.allowed_workdirs = [resolve_data_path(item, root) for item in settings.security.allowed_workdirs]
    return settings
