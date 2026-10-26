"""End-to-end MCP check with two clients and a local paird process."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
import json
from pathlib import Path
import socket
import subprocess
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


ROOT = Path(__file__).resolve().parents[1]
PORT = 8765
URL = f"http://127.0.0.1:{PORT}/mcp"


def payload(result) -> dict:
    if result.isError:
        raise AssertionError(f"MCP tool error: {result.content}")
    if result.structuredContent is not None:
        return result.structuredContent
    return json.loads(result.content[0].text)


@asynccontextmanager
async def client():
    async with streamable_http_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def wait_until_ready(process: subprocess.Popen) -> None:
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError(f"paird exited early: {process.stderr.read()}")
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.1):
                return
        except OSError:
            await asyncio.sleep(0.1)
    raise TimeoutError("paird did not start")


async def main() -> None:
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "paird.py"), "--port", str(PORT)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        await wait_until_ready(process)
        async with client() as claude, client() as codex:
            payload(await claude.call_tool("pair_join", {"session": "Smoke", "role": "claude"}))
            payload(await codex.call_tool("pair_join", {"session": "Smoke", "role": "codex"}))
            waiting = asyncio.create_task(
                codex.call_tool(
                    "pair_wait",
                    {"session": "Smoke", "role": "codex", "timeout_seconds": 5},
                    read_timeout_seconds=timedelta(seconds=8),
                )
            )
            await asyncio.sleep(0.1)
            sent = payload(await claude.call_tool("pair_send", {
                "session": "Smoke", "sender": "claude", "recipient": "codex",
                "kind": "proposal", "body": "Start with a minimal live channel",
            }))
            received = payload(await waiting)
            assert sent["sent"]["id"] == received["messages"][0]["id"]
            assert received["messages"][0]["body"] == "Start with a minimal live channel"
            print("MCP integration smoke test passed")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    asyncio.run(main())
