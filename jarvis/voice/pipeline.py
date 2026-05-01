from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path
from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, CommandResponse, TaskStatus, utc_now
from jarvis.core.service import Service

from .audio import BaseAudioSource, SoundDeviceAudioSource
from .stt import SpeechToText
from .tts import SpeechSynthesizer
from .vad import VoiceActivityDetector
from .wake_word import PorcupineWakeWordDetector, WakeWordDetector


class VoicePipeline(Service):
    def __init__(self, context: JarvisContext) -> None:
        super().__init__("jarvis.voice")
        self.context = context
        settings = context.settings.voice
        self.settings = settings
        self.wake_word = WakeWordDetector(settings.wake_word)
        self.porcupine = PorcupineWakeWordDetector(settings.wake_word)
        self.vad = VoiceActivityDetector(sample_rate=settings.sample_rate, frame_duration_ms=settings.frame_duration_ms)
        self.stt = SpeechToText(model_name=settings.stt_model, sample_rate=settings.sample_rate)
        self.tts = SpeechSynthesizer(
            model_name=settings.tts_model,
            output_dir=str(Path(context.settings.runtime.data_dir) / "voice"),
        )
        self.audio_source: BaseAudioSource = SoundDeviceAudioSource(
            sample_rate=settings.sample_rate,
            frame_duration_ms=settings.frame_duration_ms,
        )
        self._listening_task: asyncio.Task[None] | None = None
        self._state: dict[str, Any] = {
            "enabled": settings.enabled,
            "listening": False,
            "wake_word": settings.wake_word,
            "last_wake_detected_at": None,
            "last_transcript": None,
            "last_response": None,
            "last_error": None,
            "captured_segments": 0,
        }

    async def start(self) -> None:
        await super().start()
        await self.context.memory.log_activity(
            category="voice",
            message="Voice pipeline initialized.",
            details={"wake_word": self.settings.wake_word, "auto_start": self.settings.auto_start},
        )
        await self.context.bus.publish("voice.initialized", self.status_snapshot())
        if self.settings.enabled and self.settings.auto_start:
            await self.start_listening()

    async def stop(self) -> None:
        await self.stop_listening()
        self.porcupine.stop()
        await super().stop()

    async def submit_text_command(self, text: str, confirmed: bool = False) -> CommandResponse:
        if not text.strip():
            return CommandResponse(status=TaskStatus.FAILED, message="No command text provided.")
        request = CommandRequest(text=text, source="voice-text", metadata={"confirmed": confirmed})
        response = await self.context.runtime.execute_request(request)  # type: ignore[union-attr]
        self._state["last_response"] = response.message
        self.tts.speak(response.message)
        await self.context.bus.publish(
            "voice.command.completed",
            {"text": text, "status": response.status.value, "message": response.message},
        )
        return response

    async def process_transcript(
        self,
        transcript: str,
        confirmed: bool = False,
        strict_wake: bool = True,
        wake_detected: bool = False,
    ) -> CommandResponse:
        normalized = transcript.strip()
        self._state["last_transcript"] = normalized
        await self.context.bus.publish("voice.transcript.received", {"transcript": normalized, "strict_wake": strict_wake})
        if not normalized:
            return CommandResponse(status=TaskStatus.FAILED, message="No transcript text detected.")

        if wake_detected:
            cleaned = self._strip_wake_word(normalized) if self.wake_word.detect_text(normalized) else normalized
        elif self.wake_word.detect_text(normalized):
            cleaned = self._strip_wake_word(normalized)
        elif strict_wake:
            return CommandResponse(status=TaskStatus.FAILED, message="Wake word not detected.")
        else:
            cleaned = normalized

        if not cleaned:
            return CommandResponse(status=TaskStatus.FAILED, message="Wake word detected, but no command followed.")
        return await self.submit_text_command(cleaned, confirmed=confirmed)

    async def simulate_heard_text(self, transcript: str, confirmed: bool = False, strict_wake: bool = True) -> CommandResponse:
        return await self.process_transcript(transcript, confirmed=confirmed, strict_wake=strict_wake)

    async def start_listening(self) -> dict[str, Any]:
        if not self.settings.enabled:
            self._state["last_error"] = "Voice is disabled in settings."
            return self.status_snapshot()
        if self._state["listening"]:
            return self.status_snapshot()
        if not self.audio_source.provider_available:
            self._state["last_error"] = "No audio capture provider is available. Install requirements-optional.txt."
            return self.status_snapshot()

        try:
            await self.audio_source.start()
            if self.settings.use_porcupine:
                self.porcupine.start()
            self._listening_task = asyncio.create_task(self._listening_loop())
            self._state["listening"] = True
            self._state["last_error"] = None
            await self.context.memory.log_activity(category="voice", message="Voice listening started.")
            await self.context.bus.publish("voice.listening.started", self.status_snapshot())
        except Exception as exc:
            self._state["listening"] = False
            self._state["last_error"] = str(exc)
            await self.context.memory.log_activity(
                category="voice.error",
                message="Failed to start voice listening.",
                details={"error": str(exc)},
            )
        return self.status_snapshot()

    async def stop_listening(self) -> dict[str, Any]:
        if self._listening_task is not None:
            self._listening_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listening_task
            self._listening_task = None
        await self.audio_source.stop()
        self._state["listening"] = False
        await self.context.bus.publish("voice.listening.stopped", self.status_snapshot())
        return self.status_snapshot()

    def status_snapshot(self) -> dict[str, Any]:
        return {
            **self._state,
            "sample_rate": self.settings.sample_rate,
            "frame_duration_ms": self.settings.frame_duration_ms,
            "streaming": self.settings.streaming,
            "audio": self.audio_source.snapshot(),
            "wake": self.porcupine.snapshot(),
            "vad": self.vad.snapshot(),
            "stt": self.stt.snapshot(),
            "tts": self.tts.snapshot(),
        }

    async def _listening_loop(self) -> None:
        silence_frames = 0
        speech_frames: list[bytes] = []
        wake_detected = False
        max_frames = max(
            1,
            int(self.settings.max_command_seconds * 1000 / self.settings.frame_duration_ms),
        )
        try:
            while True:
                frame = await self.audio_source.read_frame(timeout=1.0)
                if frame is None:
                    continue

                if self.settings.use_porcupine and self.porcupine.detect_audio(frame):
                    wake_detected = True
                    self._state["last_wake_detected_at"] = utc_now().isoformat()
                    await self.context.bus.publish("voice.wake.detected", {"wake_word": self.settings.wake_word})
                    speech_frames = []
                    silence_frames = 0
                    continue

                is_speech = self.vad.is_speech(frame, sample_rate=self.settings.sample_rate)
                if is_speech:
                    speech_frames.append(frame)
                    silence_frames = 0
                    if len(speech_frames) >= max_frames:
                        wake_detected = await self._consume_segment(speech_frames, wake_detected=wake_detected)
                        speech_frames = []
                    continue

                if speech_frames:
                    silence_frames += 1
                    if silence_frames >= self.settings.speech_silence_frames:
                        wake_detected = await self._consume_segment(speech_frames, wake_detected=wake_detected)
                        speech_frames = []
                        silence_frames = 0
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover
            self._state["last_error"] = str(exc)
            self._state["listening"] = False
            await self.context.memory.log_activity(
                category="voice.error",
                message="Voice listening loop failed.",
                details={"error": str(exc)},
            )
            await self.context.bus.publish("voice.listening.failed", self.status_snapshot())

    async def _consume_segment(self, frames: list[bytes], wake_detected: bool) -> bool:
        pcm_bytes = b"".join(frames)
        self._state["captured_segments"] += 1
        transcript = self.stt.transcribe_pcm(pcm_bytes)
        if not transcript:
            await self.context.bus.publish("voice.segment.ignored", {"reason": "empty_transcript"})
            return False
        response = await self.process_transcript(
            transcript,
            confirmed=False,
            strict_wake=not wake_detected,
            wake_detected=wake_detected,
        )
        if response.status == TaskStatus.FAILED and response.message == "Wake word not detected.":
            await self.context.bus.publish("voice.segment.ignored", {"reason": "wake_word_missing", "transcript": transcript})
            return False
        return False

    def _strip_wake_word(self, transcript: str) -> str:
        lowered = transcript.lower()
        wake = self.settings.wake_word.lower()
        index = lowered.find(wake)
        if index == -1:
            return transcript.strip()
        cleaned = transcript[index + len(self.settings.wake_word) :]
        return cleaned.strip(" ,.:")
