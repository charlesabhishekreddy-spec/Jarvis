from __future__ import annotations

import tempfile
import wave
from pathlib import Path
from typing import Any

try:
    import whisper
except ImportError:  # pragma: no cover
    whisper = None


class SpeechToText:
    def __init__(self, model_name: str = "base", sample_rate: int = 16000) -> None:
        self.model_name = model_name
        self.sample_rate = sample_rate
        self._model = None
        self.provider_available = whisper is not None
        self._last_error: str | None = None

    def transcribe(self, audio_path: str) -> str:
        if whisper is None:
            return ""
        try:
            if self._model is None:
                self._model = whisper.load_model(self.model_name)
            result = self._model.transcribe(audio_path)
            return result.get("text", "").strip()
        except Exception as exc:  # pragma: no cover
            self._last_error = str(exc)
            return ""

    def transcribe_pcm(self, pcm_bytes: bytes) -> str:
        if not pcm_bytes:
            return ""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
            temp_path = Path(handle.name)
        try:
            with wave.open(str(temp_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(pcm_bytes)
            return self.transcribe(str(temp_path))
        finally:
            temp_path.unlink(missing_ok=True)

    def snapshot(self) -> dict[str, Any]:
        return {
            "provider": "whisper" if self.provider_available else "unavailable",
            "available": self.provider_available,
            "model": self.model_name,
            "sample_rate": self.sample_rate,
            "loaded": self._model is not None,
            "last_error": self._last_error,
        }
