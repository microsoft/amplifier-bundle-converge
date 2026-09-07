"""The five procedure skills ride with the manager mode, not with every session.

They are mid-operation manager procedures, so they are contributed by
`modes/converge-manager.md` and are absent from the always-on skills catalog a
host session renders on every request. Measured on a real session the day the
move landed (docs/lanes/qtwo-converge-catalog-reduction/): 50 skills in the
catalog before, 45 after, all five still loadable the moment the mode is on.

These tests are the standing guard on that shape. They are file-shape checks,
not a live render -- what they can prove is that the wiring still says what it
said, and drifting it back would have to happen deliberately, in the open.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BEHAVIOR = REPO / "behaviors" / "converge.yaml"
MODE = REPO / "modes" / "converge-manager.md"
SKILLS_DIR = REPO / "skills"


def _shipped_skills() -> set[str]:
    return {d.name for d in SKILLS_DIR.iterdir() if (d / "SKILL.md").is_file()}


def _mode_contributed_skills() -> set[str]:
    """Skill names in the mode's `contributes.skills` list.

    Read with a regex rather than a YAML parser on purpose: the frontmatter is
    the thing under test, and a test that needs the file to parse cleanly to
    say anything is a test that goes quiet exactly when the file breaks.
    """
    body = MODE.read_text(encoding="utf-8")
    block = re.search(
        r"^    skills:\n((?:\s*-\s*\"@converge:skills/[^\"]+\"\n)+)", body, re.MULTILINE
    )
    if not block:
        return set()
    return set(re.findall(r'"@converge:skills/([^"]+)"', block.group(1)))


def test_every_shipped_skill_is_contributed_by_the_mode():
    """A skill on disk that no mode contributes is unreachable in every session."""
    shipped = _shipped_skills()
    assert shipped, "no skills found on disk -- this test would pass vacuously"
    assert _mode_contributed_skills() == shipped


def test_the_behavior_registers_no_always_on_skills():
    """The behavior must not put converge's skills in every session's catalog.

    A `tools: - module: tool-skills` block with `config.skills` here is the
    always-on registration this change removed: it taxes the skills-visibility
    block of every session the behavior composes onto, including sessions doing
    unrelated work.
    """
    body = BEHAVIOR.read_text(encoding="utf-8")
    offending = [
        line
        for line in body.splitlines()
        if not line.lstrip().startswith("#") and "@converge:skills" in line
    ]
    assert offending == [], (
        "behaviors/converge.yaml registers converge's skills always-on again; "
        f"they belong in the mode's contributes.skills block. Lines: {offending}"
    )


def test_the_mode_can_reach_load_skill():
    """§5.5 of the mode schema: contributed skills need `load_skill` reachable.

    Satisfied here by `default_action: allow`; a `tools.safe`/`tools.warn`
    entry for `load_skill` would satisfy it too.
    """
    body = MODE.read_text(encoding="utf-8")
    frontmatter = body.split("---", 2)[1]
    assert re.search(r"^\s*default_action:\s*allow\s*$", frontmatter, re.MULTILINE) or (
        re.search(r"^\s*-\s*load_skill\s*$", frontmatter, re.MULTILINE)
    ), "contributes.skills is non-empty but load_skill is not reachable by tool policy"
