import asyncio
import unittest

from jarvis.core.events import AsyncEventBus


class EventBusTests(unittest.IsolatedAsyncioTestCase):
    async def test_open_stream_receives_matching_event(self) -> None:
        bus = AsyncEventBus()
        queue, handler = await bus.open_stream("task.*")
        try:
            await bus.publish("task.completed", {"plan_id": "123"})
            event = await asyncio.wait_for(queue.get(), timeout=1)
            payload = bus.serialize_event(event)
            self.assertEqual(payload["topic"], "task.completed")
            self.assertEqual(payload["payload"]["plan_id"], "123")
        finally:
            await bus.unsubscribe("task.*", handler)
