from __future__ import annotations

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

    def detect_audio(self, pcm_frame: list[int]) -> bool:
        if not self.provider_available:
            return False
        return False
