import asyncio
import unittest

from broker import Broker, MAX_PENDING


class BrokerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.broker = Broker()
        await self.broker.join("AdminReview", "claude")
        await self.broker.join("AdminReview", "codex")

    async def test_live_delivery_and_order(self):
        waiting = asyncio.create_task(self.broker.receive("AdminReview", "codex", 1))
        await asyncio.sleep(0)
        sent = await self.broker.send("AdminReview", "claude", "codex", "proposal", "Try approach A")
        received = await waiting
        self.assertEqual(sent["sent"]["id"], 1)
        self.assertEqual(received["messages"][0]["body"], "Try approach A")
        self.assertEqual(received["messages"][0]["kind"], "proposal")
        self.assertEqual(received["remaining"], 0)

    async def test_session_and_recipient_isolation(self):
        await self.broker.join("Other", "claude")
        await self.broker.join("Other", "codex")
        await self.broker.send("AdminReview", "claude", "codex", "task", "First")
        self.assertEqual((await self.broker.receive("Other", "codex", 0))["messages"], [])
        self.assertEqual((await self.broker.receive("AdminReview", "claude", 0))["messages"], [])
        self.assertEqual(len((await self.broker.receive("AdminReview", "codex", 0))["messages"]), 1)

    async def test_queue_capacity_rejects_without_dropping(self):
        for i in range(MAX_PENDING):
            await self.broker.send("AdminReview", "claude", "codex", "question", str(i))
        with self.assertRaisesRegex(ValueError, "full"):
            await self.broker.send("AdminReview", "claude", "codex", "question", "overflow")
        received = await self.broker.receive("AdminReview", "codex", 0, 50)
        self.assertEqual(received["messages"][0]["body"], "0")
        self.assertEqual(received["remaining"], MAX_PENDING - 50)

    async def test_validation(self):
        with self.assertRaises(ValueError):
            await self.broker.join("bad/name", "claude")
        with self.assertRaises(ValueError):
            await self.broker.send("AdminReview", "claude", "claude", "task", "No")
        with self.assertRaises(ValueError):
            await self.broker.receive("AdminReview", "codex", 26)


if __name__ == "__main__":
    unittest.main()
