"""Write two: raise or lower a priority, with a note.

This goes to the work queue itself, through the same command line the manager
session uses. The page keeps no order of its own — if it did, the queue and the
page would disagree the moment either moved.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .result import WriteResult

CLI = "amplifier-work-tracker"
DIRECTIONS = ("sooner", "later")


def signal_priority(
    repo: Path,
    project: str,
    item_id: str,
    direction: str,
    note: str = "",
    actor: str = "the steward, from the companion page",
) -> WriteResult:
    direction = (direction or "").strip().lower()
    if direction not in DIRECTIONS:
        return WriteResult.failed("A priority signal is either sooner or later.")
    if not item_id.strip():
        return WriteResult.failed("A priority signal needs to name the piece of work it is about.")
    if shutil.which(CLI) is None:
        return WriteResult.failed(
            f"The work queue cannot be reached: `{CLI}` is not installed on this machine. "
            "Nothing was changed."
        )

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    line = f"Priority: {direction} — asked by the steward, {stamp}."
    if note.strip():
        line += f" {note.strip()}"

    try:
        current = subprocess.run(
            [CLI, "list", "--project", project, "--id", item_id, "--json"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return WriteResult.failed(f"The work queue could not be read, so nothing was changed: {exc}.")
    if current.returncode != 0:
        return WriteResult.failed(
            f"The work queue does not know about “{item_id}”, so nothing was changed."
        )

    import json

    try:
        record = json.loads(current.stdout or "{}")
    except json.JSONDecodeError:
        return WriteResult.failed("The work queue answered with something we could not read; nothing was changed.")
    item = record.get("item", record)
    description = (item.get("description") or "").rstrip()
    updated = f"{description}\n\n{line}".strip()

    try:
        result = subprocess.run(
            [
                CLI,
                "edit",
                "--project",
                project,
                "--id",
                item_id,
                "--description",
                updated,
                "--actor",
                actor,
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return WriteResult.failed(f"The priority signal did not land: {exc}.")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        return WriteResult.failed(
            "The priority signal did not land: "
            + (detail[0] if detail else "the work queue refused it.")
        )

    return WriteResult(
        ok=True,
        message=f"Asked for “{item_id}” {direction}.",
        where=f"the work queue, project {project}",
    )
