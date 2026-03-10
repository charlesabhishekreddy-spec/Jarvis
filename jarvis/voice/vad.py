from __future__ import annotations

try:
    import webrtcvad
except ImportError:  # pragma: no cover
    webrtcvad = None


class VoiceActivityDetector:
    def __init__(self) -> None:
        self.provider_available = webrtcvad is not None

    def is_speech(self, frame: bytes, sample_rate: int = 16000) -> bool:
        if webrtcvad is None:
            return bool(frame)
        detector = webrtcvad.Vad(2)
        return detector.is_speech(frame, sample_rate)
