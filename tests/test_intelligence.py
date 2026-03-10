import unittest

from jarvis.brain.intelligence import HeuristicReasoningProvider


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
