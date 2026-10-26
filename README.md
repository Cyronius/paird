# paird

`paird` gives Claude Code and Codex a live, local pair-programming channel. One Python process keeps named sessions and pending messages in memory and exposes four MCP tools: `pair_join`, `pair_send`, `pair_wait`, and `pair_status`. Both agents connect to the same server over loopback TCP, so the setup works on Windows, macOS, and Linux. The included `pairprogram` skill tells each agent how to propose, critique, agree on a plan, hand off work, and review results.

## Requirements

- Python 3.11 or newer
- Claude Code and Codex CLI, already installed and signed in
- Both agents running on the same machine, or both able to reach the same broker address

`paird` itself makes no model API calls. The two agent sessions may consume subscription usage or incur API charges according to how they are configured.

## Install and start

Run these commands from the `paird` directory. On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe paird.py
```

On macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python paird.py
```

Leave that terminal running. The server listens only on `127.0.0.1:8765` and serves MCP at `http://127.0.0.1:8765/mcp`. Choose another port with `--port NUMBER` and change the URLs below to match.

## Connect both agents

From the `paird` directory, install the skill into the coding project using the Python interpreter you used above:

```text
python install_skill.py --project PATH_TO_CODING_PROJECT
```

On Windows, `python` may be `py -3`; on macOS or Linux, it may be `python3`. The installer copies the same skill into `.claude/skills/pairprogram/SKILL.md` and `.codex/skills/pairprogram/SKILL.md` in the target project. To make the skill available in every project, use `python install_skill.py --user` instead.

Then, in a terminal in the coding project, register the MCP server with each CLI:

```text
claude mcp add --transport http paird http://127.0.0.1:8765/mcp
codex mcp add paird --url http://127.0.0.1:8765/mcp
```

Restart the agent sessions after installing skills or MCP configuration.

## Start a pair session

Open two terminals in the same coding project. Start the agents with the models and effort you want:

```text
claude --model opus --effort xhigh
codex -m gpt-6-sol -c model_reasoning_effort=xhigh
```

Then enter a named invocation in each session:

```text
Claude: /pairprogram AdminReview
Codex:  $pairprogram AdminReview
```

Give either agent the task, for example: `Investigate the failing admin review flow with your pair. Agree on a plan before editing.` That agent sends the task to its peer. Both sessions must remain active and call `pair_wait` to receive messages. You can send follow-up prompts to either agent; its client may queue them until the current turn finishes.

Each message has a `kind`: `task`, `proposal`, `critique`, `plan`, `ack`, `handoff`, `review`, `question`, or `answer`. A plan is agreed only after the other agent acknowledges it. For independent edits, assign different files or Git worktrees before either agent writes.

## Limits and troubleshooting

- The channel is live and memory-only. Restarting `paird` clears sessions and pending messages. Rejoin from both agents after a restart.
- Messages are delivered when an agent calls `pair_wait`. The broker does not wake a stopped or completed model turn; automatic wakeups require a session controller around the CLIs.
- A `pair_wait` call waits up to 25 seconds. Have the agents call it again while expecting a reply.
- Keep the broker on loopback. It has no authentication and is intended for two locally trusted agent processes. If one agent runs in WSL or a container, ensure both can reach the same address; `127.0.0.1` may refer to different network namespaces.
- Check `claude mcp list` and `codex mcp list` if a tool is missing. Check that the broker terminal still shows a running server and both clients use the same port.

Run the local broker tests with `python -m unittest discover -s tests -v`. Run `python tests/integration_smoke.py` to start a temporary broker and verify message delivery through two MCP clients. Use the environment's Python interpreter for both commands.
