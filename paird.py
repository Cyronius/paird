"""Run paird as a localhost Streamable HTTP MCP server."""

from __future__ import annotations

import argparse

from mcp.server.fastmcp import FastMCP

from broker import Broker


def main() -> None:
    parser = argparse.ArgumentParser(description="Local live channel for Claude Code and Codex")
    parser.add_argument("--port", type=int, default=8765, help="TCP port on 127.0.0.1 (default: 8765)")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    broker = Broker()
    server = FastMCP("paird", host="127.0.0.1", port=args.port, stateless_http=True, json_response=True)

    @server.tool()
    async def pair_join(session: str, role: str) -> dict:
        """Join a named two-agent session as 'claude' or 'codex'. Call this before send or receive."""
        return await broker.join(session, role)

    @server.tool()
    async def pair_send(session: str, sender: str, recipient: str, kind: str, body: str) -> dict:
        """Send a live message to the other agent. Kinds: task, proposal, critique, plan, ack, handoff, review, question, answer."""
        return await broker.send(session, sender, recipient, kind, body)

    @server.tool()
    async def pair_wait(session: str, role: str, timeout_seconds: float = 15, limit: int = 10) -> dict:
        """Receive queued messages, waiting up to 25 seconds. An empty list means no message arrived yet."""
        return await broker.receive(session, role, timeout_seconds, limit)

    @server.tool()
    async def pair_status(session: str) -> dict:
        """Show joined roles and pending message counts for a named session."""
        return await broker.status(session)

    print(f"paird listening at http://127.0.0.1:{args.port}/mcp", flush=True)
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
