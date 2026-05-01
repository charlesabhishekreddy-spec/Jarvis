from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover
    sd = None


class BaseAudioSource:
    def __init__(self, sample_rate: int = 16000, frame_duration_ms: int = 30) -> None:
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_samples = int(sample_rate * frame_duration_ms / 1000)
        self.provider_name = "base"
        self.provider_available = False

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def read_frame(self, timeout: float = 1.0) -> bytes | None:
        return None

    def snapshot(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "available": self.provider_available,
            "sample_rate": self.sample_rate,
            "frame_duration_ms": self.frame_duration_ms,
        }


class SoundDeviceAudioSource(BaseAudioSource):
    def __init__(self, sample_rate: int = 16000, frame_duration_ms: int = 30) -> None:
        super().__init__(sample_rate=sample_rate, frame_duration_ms=frame_duration_ms)
        self.provider_name = "sounddevice"
        self.provider_available = sd is not None
        self._queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=200)
        self._stream = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._last_error: str | None = None

    async def start(self) -> None:
        if not self.provider_available:
            raise RuntimeError("sounddevice is not installed.")
        if self._stream is not None:
            return
        self._loop = asyncio.get_running_loop()

        def callback(indata, frames, time_info, status) -> None:  # pragma: no cover
            if status:
                self._last_error = str(status)
            payload = bytes(indata)
            if self._loop is None:
                return

            def enqueue() -> None:
                with suppress(asyncio.QueueFull):
                    self._queue.put_nowait(payload)

            self._loop.call_soon_threadsafe(enqueue)

        self._stream = sd.RawInputStream(  # pragma: no cover
            samplerate=self.sample_rate,
            blocksize=self.frame_samples,
            channels=1,
            dtype="int16",
            callback=callback,
        )
        self._stream.start()

    async def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()  # pragma: no cover
            self._stream.close()  # pragma: no cover
            self._stream = None
        while not self._queue.empty():
            with suppress(asyncio.QueueEmpty):
                self._queue.get_nowait()
                self._queue.task_done()

    async def read_frame(self, timeout: float = 1.0) -> bytes | None:
        if self._stream is None:
            return None
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def snapshot(self) -> dict[str, Any]:
        snapshot = super().snapshot()
        snapshot.update({"active": self._stream is not None, "last_error": self._last_error})
        return snapshot
