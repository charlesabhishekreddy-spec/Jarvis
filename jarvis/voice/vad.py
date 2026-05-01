from __future__ import annotations

try:
    import webrtcvad
except ImportError:  # pragma: no cover
    webrtcvad = None


class VoiceActivityDetector:
    def __init__(self, aggressiveness: int = 2, sample_rate: int = 16000, frame_duration_ms: int = 30) -> None:
        self.provider_available = webrtcvad is not None
        self.provider_name = "webrtcvad" if self.provider_available else "fallback"
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.aggressiveness = aggressiveness
        self._detector = webrtcvad.Vad(aggressiveness) if webrtcvad is not None else None

    def is_speech(self, frame: bytes, sample_rate: int = 16000) -> bool:
        if webrtcvad is None:
            return bool(frame)
        return self._detector.is_speech(frame, sample_rate)

    def snapshot(self) -> dict[str, int | bool | str]:
        return {
            "provider": self.provider_name,
            "available": self.provider_available,
            "sample_rate": self.sample_rate,
            "frame_duration_ms": self.frame_duration_ms,
            "aggressiveness": self.aggressiveness,
        }
