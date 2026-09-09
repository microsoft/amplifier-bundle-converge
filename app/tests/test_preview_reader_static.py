"""converge-43uv — structural regression, no browser required.

The reader lane's acceptance is mostly about runtime behaviour (a menu that
opens, a badge that reads correctly against live data, a message that changes
once a fetch settles) and those checks belong in
``test_preview_reader_rendered.py``, gated on Playwright like every other
rendered-browser test in this app. But four of the five acceptance items also
have a STATIC shape — markup that is either there or not, regardless of
whether a browser ever executes the page's JS — and that shape is worth
pinning without paying for a browser at all: it runs in the plain
``app/tests`` suite, every time, on every host, and it is what actually
caught the misleading nav duplicates and the conflated badge in the first
place (they were markup facts, not runtime ones).

Real app, real template, real Jinja render via `TestClient` — the same
pattern `test_api.py` uses. Nothing here is a fixture of the server's own
answer: the HTML asserted against is exactly what `app/serve.py` would send
a signed-in browser.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, serve  # noqa: E402

USER = "tester"

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def project(tmp_path: Path) -> dict:
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text("# Highway\n\n## Outcome\nShip the reader.\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text(MANIFEST_HEAD, encoding="utf-8")

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tracker_project = ""\n'
        'tmux_socket = "test-socket-that-does-not-exist"\n',
        encoding="utf-8",
    )
    return {
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json", "sessions": tmp_path / "sessions.json",
    }


class _FakePam:
    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        return username == USER and password == "correct horse"


@pytest.fixture
def client(project, monkeypatch) -> TestClient:
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"], sessions_path=project["sessions"]
    )
    tc = TestClient(made, follow_redirects=False)
    answer = tc.post("/login", data={"username": USER, "password": "correct horse", "next": "/"})
    assert answer.status_code == 302, "the fixture user could not sign in at all"
    return tc


def _direction_html(client: TestClient) -> str:
    answer = client.get("/")
    assert answer.status_code == 200, f"the shell did not serve: {answer.status_code}"
    return answer.text


# --------------------------------------------------------------------------
# acceptance 1 — an accessible Tools menu, Raw and the four modes stay direct
# --------------------------------------------------------------------------


def test_the_tools_menu_holds_the_four_folded_controls(client: TestClient) -> None:
    """Wide · Copy rendered · Copy source · Download · zoom sit inside one
    accessible disclosure — a native `<details>`, so no ARIA has to be hand
    wired for it to be keyboard-operable."""
    html = _direction_html(client)
    menu_start = html.index('id="toolsMenu"')
    menu_open = html.rindex("<details", 0, menu_start)
    menu_close = html.index("</details>", menu_start)
    menu = html[menu_open:menu_close]
    print(f"\n[tools menu] {len(menu)} chars")
    assert menu.startswith("<details"), "the Tools menu is not a <details> disclosure"
    for control in ("wideToggle", "copyRendered", "copySource", "downloadDoc", "zoomIn", "zoomOut"):
        assert f'id="{control}"' in menu, f"#{control} is not inside the Tools menu"


def test_raw_and_the_four_modes_are_not_inside_the_tools_menu(client: TestClient) -> None:
    """Raw and the mode tabs stay direct controls — never folded away."""
    html = _direction_html(client)
    menu_start = html.index('id="toolsMenu"')
    menu_open = html.rindex("<details", 0, menu_start)
    menu_close = html.index("</details>", menu_start)
    menu = html[menu_open:menu_close]
    for direct in ("rawToggle", "askButton"):
        assert f'id="{direct}"' not in menu, f"#{direct} was folded into the Tools menu"
    # Raw sits beside Read, in the mode-tabs bar, per acceptance 1's own words.
    tabs_start = html.index('class="mode-tabs"')
    tabs_close = html.index("</div>", tabs_start)
    tabs = html[tabs_start:tabs_close]
    assert 'id="rawToggle"' in tabs, "Raw is not beside the Read tab"
    assert tabs.index('id="rawToggle"') < tabs.index('data-doc-mode="read"'), (
        "Raw does not sit beside (before) Read"
    )
    for mode in ("read", "changes", "review", "history"):
        assert f'data-doc-mode="{mode}"' in html, f"the {mode} mode tab is missing"


# --------------------------------------------------------------------------
# acceptance 2 — no misleading duplicate nav, auxiliary context collapsed
# --------------------------------------------------------------------------


def test_the_duplicate_nav_utilities_are_gone(client: TestClient) -> None:
    """'All changes' / 'Proposals' / 'My decisions' duplicated the mode tabs
    while claiming a wider scope ('All changes' opened only the current
    document) — removed rather than relabelled, since the mode tabs already
    do the same job honestly."""
    html = _direction_html(client)
    assert "data-nav-special" not in html, "a misleading nav-utilities control is still served"
    assert 'id="allChangesCount"' not in html
    assert 'id="proposalCountNav"' not in html
    assert 'id="decisionsCountNav"' not in html


def test_project_reality_is_collapsed_auxiliary_detail(client: TestClient) -> None:
    """Project-wide reality counts are not evidence about the one document on
    screen — collapsed behind a native disclosure rather than sitting open."""
    html = _direction_html(client)
    card_start = html.index('id="realityKept"')
    card_open = html.rindex("<details", 0, card_start)
    assert "aux-detail" in html[card_open : card_open + 200], (
        "the Reality card is not marked as collapsed auxiliary detail"
    )


# --------------------------------------------------------------------------
# acceptance 3 — agreement and conformance are two distinct badges
# --------------------------------------------------------------------------


def test_agreement_and_conformance_are_two_separate_badges(client: TestClient) -> None:
    """One conflated badge used to answer both "is this locked?" and "is this
    promise being kept?" at once. Two spans now, each with its own id, each
    with a title naming its own question — so a test (or a steward) can never
    mistake one dimension's answer for the other's."""
    html = _direction_html(client)
    assert 'id="docStateBadge"' in html, "the agreement badge is missing"
    assert 'id="docConformanceBadge"' in html, "the conformance badge is missing"
    assert html.index('id="docStateBadge"') != html.index('id="docConformanceBadge"')
    badge_region = html[html.index('class="title-meta"') : html.index('class="title-meta"') + 700]
    assert "docStateBadge" in badge_region and "docConformanceBadge" in badge_region, (
        "the two badges are not both in the document's title-meta row"
    )


# --------------------------------------------------------------------------
# acceptance 5 — nothing named here was quietly deleted
# --------------------------------------------------------------------------


def test_lock_gate_ask_and_history_controls_still_render(client: TestClient) -> None:
    """The lock gate, Ask, and History are untouched by this lane's changes —
    a fast tripwire against an edit that accidentally dropped one."""
    html = _direction_html(client)
    for still_there in (
        'id="lockGate"',
        'id="lockButton"',
        'data-ask',
        'data-doc-mode="history"',
        'id="bookmarkButton"',
    ):
        assert still_there in html, f"{still_there} is missing from the served page"
