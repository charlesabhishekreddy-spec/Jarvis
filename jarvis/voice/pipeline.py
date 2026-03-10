from __future__ import annotations

from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, CommandResponse, TaskStatus
from jarvis.core.service import Service

from .stt import SpeechToText
from .tts import SpeechSynthesizer
from .vad import VoiceActivityDetector
from .wake_word import PorcupineWakeWordDetector, WakeWordDetector


class VoicePipeline(Service):
    def __init__(self, context: JarvisContext) -> None:
        super().__init__("jarvis.voice")
        self.context = context
        self.wake_word = WakeWordDetector(context.settings.voice.wake_word)
        self.porcupine = PorcupineWakeWordDetector(context.settings.voice.wake_word)
        self.vad = VoiceActivityDetector()
        self.stt = SpeechToText()
        self.tts = SpeechSynthesizer()

    async def start(self) -> None:
        await super().start()
        await self.context.memory.log_activity(
            category="voice",
            message="Voice pipeline initialized.",
            details={"wake_word": self.context.settings.voice.wake_word},
        )

    async def submit_text_command(self, text: str, confirmed: bool = False) -> CommandResponse:
        if not text.strip():
            return CommandResponse(status=TaskStatus.FAILED, message="No command text provided.")
        request = CommandRequest(text=text, source="voice-text", metadata={"confirmed": confirmed})
        response = await self.context.runtime.execute_request(request)  # type: ignore[union-attr]
        self.tts.speak(response.message)
        return response

    async def process_transcript(self, transcript: str) -> CommandResponse:
        if self.wake_word.detect_text(transcript):
            cleaned = transcript.lower().replace(self.context.settings.voice.wake_word.lower(), "", 1).strip(", ")
            return await self.submit_text_command(cleaned)
        return CommandResponse(status=TaskStatus.FAILED, message="Wake word not detected.")
