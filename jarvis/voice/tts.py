from __future__ import annotations

try:
    from TTS.api import TTS
except ImportError:  # pragma: no cover
    TTS = None


class SpeechSynthesizer:
    def __init__(self) -> None:
        self.provider_available = TTS is not None

    def speak(self, text: str) -> None:
        if not text:
            return
        if TTS is None:
            print(f"JARVIS: {text}")
            return
        synthesizer = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
        synthesizer.tts_to_file(text=text, file_path="jarvis_tts_output.wav")
