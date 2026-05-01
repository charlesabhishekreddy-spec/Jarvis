import unittest

from jarvis.brain.intelligence import GeminiReasoningProvider, HeuristicReasoningProvider, IntelligenceService
from jarvis.core.config import IntelligenceSettings


class FakeGeminiProvider(GeminiReasoningProvider):
    def __init__(self, response_payload: dict) -> None:
        super().__init__(
            model="gemini-2.5-flash",
            endpoint="https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            api_key="test-key",
            timeout_seconds=1,
        )
        self.response_payload = response_payload
        self.last_payload: dict | None = None

    def _post_json(self, payload: dict) -> dict:
        self.last_payload = payload
        return self.response_payload


class IntelligenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_heuristic_report_summary(self) -> None:
        provider = HeuristicReasoningProvider()
        result = await provider.summarize(
            "prepare a report about renewable energy",
            [
                "Renewable energy investment increased in several regions.",
                "Solar deployment accelerated and grid storage improved reliability.",
            ],
            context={"memories": [{"content": "The user prefers concise reports."}]},
        )

        self.assertIn("# Report", result.text)
        self.assertIn("Renewable energy investment increased", result.text)

    async def test_gemini_response_parses_text(self) -> None:
        provider = FakeGeminiProvider(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "Gemini says hello."},
                            ]
                        },
                        "finishReason": "STOP",
                    }
                ]
            }
        )

        result = await provider.respond("Hello", context={"memories": [{"content": "The user likes concise answers."}]})

        self.assertEqual(result.provider, "gemini")
        self.assertEqual(result.text, "Gemini says hello.")
        self.assertEqual(result.metadata["finish_reason"], "STOP")
        assert provider.last_payload is not None
        self.assertEqual(provider.last_payload["contents"][0]["role"], "user")
        self.assertIn("Relevant memory:", provider.last_payload["contents"][0]["parts"][0]["text"])

    async def test_gemini_tool_planning_parses_json(self) -> None:
        provider = FakeGeminiProvider(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"tool_calls":[{"name":"memory.recall","arguments":{"query":"editor"},"reason":"Find the stored preference."}]}'
                                }
                            ]
                        }
                    }
                ]
            }
        )

        calls = await provider.plan_tool_usage(
            "What did I say about editor",
            [{"name": "memory.recall", "description": "Search memory."}],
            max_calls=2,
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "memory.recall")
        self.assertEqual(calls[0].arguments["query"], "editor")

    async def test_service_falls_back_without_gemini_key(self) -> None:
        settings = IntelligenceSettings(
            provider="gemini",
            model="gemini-2.5-flash",
            endpoint="https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            timeout_seconds=5,
        )

        service = IntelligenceService(settings, gemini_api_key="")
        self.assertEqual(service.provider.name, "heuristic")
