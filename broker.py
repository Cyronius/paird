"""In-memory, two-party message broker for paird."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import re


ROLES = {"claude", "codex"}
KINDS = {"task", "proposal", "critique", "plan", "ack", "handoff", "review", "question", "answer"}
SESSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
MAX_BODY = 16_000
MAX_PENDING = 200


@dataclass(frozen=True)
class Message:
    id: int
    session: str
    sender: str
    recipient: str
    kind: str
    body: str
    sent_at: str


@dataclass
class Session:
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    joined: set[str] = field(default_factory=set)
    pending: dict[str, deque[Message]] = field(
        default_factory=lambda: {role: deque() for role in ROLES}
    )
    next_id: int = 1


class Broker:
    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}

    @staticmethod
    def _session_name(name: str) -> str:
        if not SESSION_PATTERN.fullmatch(name):
            raise ValueError("Session must be 1-64 letters, digits, underscores, or hyphens and start with a letter or digit")
        return name

    @staticmethod
    def _role(role: str) -> str:
        if role not in ROLES:
            raise ValueError("Role must be 'claude' or 'codex'")
        return role

    def _get(self, name: str) -> Session:
        self._session_name(name)
        try:
            return self.sessions[name]
        except KeyError as exc:
            raise ValueError(f"Unknown session: {name}. Join it first.") from exc

    async def join(self, name: str, role: str) -> dict:
        self._session_name(name)
        self._role(role)
        session = self.sessions.setdefault(name, Session())
        async with session.condition:
            session.joined.add(role)
            return self._status(name, session)

    @staticmethod
    def _status(name: str, session: Session) -> dict:
        return {
            "session": name,
            "joined": sorted(session.joined),
            "pending": {role: len(session.pending[role]) for role in sorted(ROLES)},
        }

    async def status(self, name: str) -> dict:
        session = self._get(name)
        async with session.condition:
            return self._status(name, session)

    async def send(self, name: str, sender: str, recipient: str, kind: str, body: str) -> dict:
        session = self._get(name)
        self._role(sender)
        self._role(recipient)
        if sender == recipient:
            raise ValueError("Sender and recipient must differ")
        if kind not in KINDS:
            raise ValueError(f"Kind must be one of: {', '.join(sorted(KINDS))}")
        if not body or len(body) > MAX_BODY:
            raise ValueError(f"Body must contain 1-{MAX_BODY} characters")
        async with session.condition:
            if sender not in session.joined:
                raise ValueError(f"{sender} has not joined {name}")
            queue = session.pending[recipient]
            if len(queue) >= MAX_PENDING:
                raise ValueError(f"{recipient}'s pending queue is full; ask them to receive messages")
            message = Message(
                id=session.next_id,
                session=name,
                sender=sender,
                recipient=recipient,
                kind=kind,
                body=body,
                sent_at=datetime.now(timezone.utc).isoformat(),
            )
            session.next_id += 1
            queue.append(message)
            session.condition.notify_all()
            return {"sent": asdict(message), "recipient_joined": recipient in session.joined}

    async def receive(self, name: str, role: str, timeout_seconds: float = 15, limit: int = 10) -> dict:
        session = self._get(name)
        self._role(role)
        if not 0 <= timeout_seconds <= 25:
            raise ValueError("timeout_seconds must be between 0 and 25")
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        async with session.condition:
            if role not in session.joined:
                raise ValueError(f"{role} has not joined {name}")
            if not session.pending[role] and timeout_seconds:
                try:
                    await asyncio.wait_for(
                        session.condition.wait_for(lambda: bool(session.pending[role])),
                        timeout_seconds,
                    )
                except TimeoutError:
                    pass
            messages = []
            queue = session.pending[role]
            for _ in range(min(limit, len(queue))):
                messages.append(asdict(queue.popleft()))
            return {"session": name, "role": role, "messages": messages, "remaining": len(queue)}
