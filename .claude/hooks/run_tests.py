#!/usr/bin/env python3
"""Stop hook: run the test suite; if it fails, block the stop and hand Claude the failure.

Output shape per the Claude Code hooks reference (Stop decision control):
    {"decision": "block", "reason": "<why Claude should keep working>"}
printed to stdout with exit code 0. Printing nothing and exiting 0 lets Claude stop.

stop_hook_active is true when Claude is already continuing because of a stop hook.
In that case we do not block again: Claude has had its chance to fix the tests or say
it could not (CLAUDE.md working agreements), and re-blocking could loop on a failure
that never resolves. Claude Code also caps consecutive stop-hook continuations at 8.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

TEST_PATHS = ["tests/unit", "tests/api"]
TIMEOUT_SECONDS = 120
MAX_REASON_CHARS = 6000
# pytest exit codes: 0 = all passed, 5 = no tests collected. Everything else is a problem.
OK_EXIT_CODES = {0, 5}


def project_dir(hook_input: dict) -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or hook_input.get("cwd") or os.getcwd())


def python_for(project: Path) -> str:
    """Prefer the project's virtualenv so pytest and snip resolve the way they do for the team."""
    for candidate in (project / ".venv" / "Scripts" / "python.exe", project / ".venv" / "bin" / "python"):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        hook_input = {}

    if hook_input.get("stop_hook_active"):
        return 0

    project = project_dir(hook_input)
    cmd = [python_for(project), "-m", "pytest", *TEST_PATHS, "-q", "-p", "no:cacheprovider"]

    try:
        result = subprocess.run(
            cmd,
            cwd=project,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        block(f"Test suite did not finish within {TIMEOUT_SECONDS}s. Find what hangs, fix it or say clearly that you could not.")
        return 0

    if result.returncode in OK_EXIT_CODES:
        return 0

    output = (result.stdout + result.stderr).strip()
    if len(output) > MAX_REASON_CHARS:
        output = "...(truncated)...\n" + output[-MAX_REASON_CHARS:]
    block(
        f"The test suite failed (pytest exit code {result.returncode}). "
        "Fix the failing tests, or say clearly that you could not.\n\n" + output
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
