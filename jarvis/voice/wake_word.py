from __future__ import annotations

from array import array
from typing import Any

try:
    import pvporcupine
except ImportError:  # pragma: no cover
    pvporcupine = None


class WakeWordDetector:
    def __init__(self, wake_word: str = "hey jarvis") -> None:
        self.wake_word = wake_word.lower()

    def detect_text(self, text: str) -> bool:
        return self.wake_word in text.lower()


class PorcupineWakeWordDetector(WakeWordDetector):
    def __init__(self, wake_word: str = "hey jarvis") -> None:
        super().__init__(wake_word)
        self.provider_available = pvporcupine is not None
        self._engine = None
        self._last_error: str | None = None

    def start(self) -> None:
        if not self.provider_available or self._engine is not None:
            return
        try:
            keyword = "jarvis" if "jarvis" in self.wake_word else self.wake_word.replace(" ", "_")
            self._engine = pvporcupine.create(keywords=[keyword])  # pragma: no cover
        except Exception as exc:  # pragma: no cover
            self._last_error = str(exc)
            self._engine = None

    def stop(self) -> None:
        if self._engine is None:
            return
        try:
            self._engine.delete()  # pragma: no cover
        finally:
            self._engine = None

    def detect_audio(self, pcm_frame: bytes | list[int]) -> bool:
        if not self.provider_available or self._engine is None:
            return False
        if isinstance(pcm_frame, bytes):
            samples = array("h")
            samples.frombytes(pcm_frame[: self._engine.frame_length * 2])  # pragma: no cover
            pcm_values = samples.tolist()
        else:
            pcm_values = pcm_frame
        if len(pcm_values) < self._engine.frame_length:
            return False
        return self._engine.process(pcm_values[: self._engine.frame_length]) >= 0  # pragma: no cover

    def snapshot(self) -> dict[str, Any]:
        return {
            "provider": "porcupine",
            "available": self.provider_available,
            "active": self._engine is not None,
            "last_error": self._last_error,
            "wake_word": self.wake_word,
        }
