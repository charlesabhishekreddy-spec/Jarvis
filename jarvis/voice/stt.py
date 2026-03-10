from __future__ import annotations

from typing import Any

try:
    import whisper
except ImportError:  # pragma: no cover
    whisper = None


class SpeechToText:
    def __init__(self, model_name: str = "base") -> None:
        self.model_name = model_name
        self._model = None

    def transcribe(self, audio_path: str) -> str:
        if whisper is None:
            return ""
        if self._model is None:
            self._model = whisper.load_model(self.model_name)
        result = self._model.transcribe(audio_path)
        return result.get("text", "").strip()
