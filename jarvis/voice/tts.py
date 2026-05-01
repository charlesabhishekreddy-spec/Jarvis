from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from TTS.api import TTS
except ImportError:  # pragma: no cover
    TTS = None


class SpeechSynthesizer:
    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC", output_dir: str | None = None) -> None:
        self.model_name = model_name
        self.output_dir = Path(output_dir).resolve() if output_dir else None
        self.provider_available = TTS is not None
        self._synthesizer = None
        self._last_output_path: str | None = None
        self._last_error: str | None = None

    def speak(self, text: str) -> dict[str, Any]:
        if not text:
            return {"ok": False, "error": "No text provided."}
        if TTS is None:
            print(f"JARVIS: {text}")
            return {"ok": True, "provider": "console", "path": None}
        try:
            if self._synthesizer is None:
                self._synthesizer = TTS(model_name=self.model_name)  # pragma: no cover
            if self.output_dir is not None:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                target = self.output_dir / "jarvis_tts_output.wav"
            else:
                target = Path("jarvis_tts_output.wav").resolve()
            self._synthesizer.tts_to_file(text=text, file_path=str(target))  # pragma: no cover
            self._last_output_path = str(target)
            return {"ok": True, "provider": "coqui", "path": self._last_output_path}
        except Exception as exc:  # pragma: no cover
            self._last_error = str(exc)
            return {"ok": False, "error": self._last_error}

    def snapshot(self) -> dict[str, Any]:
        return {
            "provider": "coqui" if self.provider_available else "console",
            "available": self.provider_available,
            "model": self.model_name,
            "loaded": self._synthesizer is not None,
            "last_output_path": self._last_output_path,
            "last_error": self._last_error,
        }
