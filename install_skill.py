"""Copy the shared pairprogram skill to Claude Code and Codex discovery paths."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def main() -> None:
    parser = argparse.ArgumentParser(description="Install the pairprogram skill for both coding agents")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", type=Path, help="Git project in which both agents will work")
    group.add_argument("--user", action="store_true", help="Install for all projects under the current user")
    args = parser.parse_args()

    source = Path(__file__).parent / "skill" / "pairprogram" / "SKILL.md"
    root = Path.home() if args.user else args.project.resolve()
    if not root.is_dir():
        parser.error(f"Target directory does not exist: {root}")
    for agent in ("claude", "codex"):
        destination = root / f".{agent}" / "skills" / "pairprogram" / "SKILL.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        print(destination)


if __name__ == "__main__":
    main()
