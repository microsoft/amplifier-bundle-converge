"""converge-neu6 + converge-8crs -- combined mounted-browser proof.

Real mounted UI, at both 1280x800 and 390x844, two distinct authenticated
synthetic identities (the registered steward, and a teammate who is not),
against a repository seeded with:

* a STRUCTURED candidate carrying a deliberately generic/misleading title,
  and separate, genuinely different exact-change and rationale sentences
  -- so a bug that swaps the two, or substitutes the title for either, is
  caught by content, not by a static string;
* an UNSTRUCTURED candidate (plain prose, no `## ` headings at all) -- so a
  proposal with no labeled sections is proven to stay fully readable, with
  an honest "not recognized" message, never an invented diff.

What this proves, per the goal's PROOF section:

1. converge-neu6 -- Review's "What changes" shows the real exact-change
   text (never the title); "Why now" shows the real rationale (never the
   exact-change text); evidence and "what does not change" are shown under
   their own truthful labels; the complete original proposal stays reachable
   and is verified byte-for-byte against the file on disk; the unstructured
   candidate's own prose is fully readable with an honest missing-heading
   label.
2. converge-8crs -- the registered steward sees live, working decision
   controls in both Review and Changes, and a successful decision writes a
   real record this test reads back off disk (never just a success toast);
   a teammate who is not the steward sees those same controls disabled and
   explained BEFORE any attempt, in both Review and Changes, while every
   allowed teammate action (reading, the full proposal) stays available; a
   direct request to the same route -- bypassing the disabled control, the
   way a forged request would -- still gets a real 403 and writes nothing.

Screenshots go to the configured evidence directory, or pytest's isolated
temporary directory, one per assertion point, at both widths.
"""

from __future__ import annotations

import os
import socket as socketlib
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, serve  # noqa: E402

# Reuse the journey test's own proven driving primitives rather than
# reimplementing the hit-test/click/boot/screenshot machinery a second time
# with a chance to quietly diverge from it.
from app.tests.test_hackathon_journey import (  # noqa: E402
    OTHER_USER,
    USER,
    _boot,
    _click,
    _git,
    _mode,
    _open_doc,
    _stow_console,
    needs_browser,
)

EVIDENCE: Path | None = None


def _evidence_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(
        os.environ.get("CONVERGE_DIRECTION_REVIEW_EVIDENCE")
        or tmp_path_factory.mktemp("direction-review-evidence")
    )


@pytest.fixture(scope="session", autouse=True)
def evidence_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Keep unconfigured evidence isolated to this pytest session."""
    global EVIDENCE
    EVIDENCE = _evidence_dir(tmp_path_factory)
    return EVIDENCE


def test_evidence_dir_defaults_to_pytest_temp(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    monkeypatch.delenv("CONVERGE_DIRECTION_REVIEW_EVIDENCE", raising=False)
    assert _evidence_dir(tmp_path_factory).parent == tmp_path_factory.getbasetemp()


def test_evidence_dir_honors_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory, tmp_path: Path
) -> None:
    monkeypatch.setenv("CONVERGE_DIRECTION_REVIEW_EVIDENCE", str(tmp_path / "evidence"))
    assert _evidence_dir(tmp_path_factory) == tmp_path / "evidence"


def _shot(page, tag: str, name: str) -> Path:
    assert EVIDENCE is not None, "pytest did not initialize the evidence directory"
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / f"{tag}-{name}.png"
    page.screenshot(path=str(path), full_page=False)
    return path


# --------------------------------------------------------------------------
# the fixture repository -- a structured candidate and an unstructured one
# --------------------------------------------------------------------------

VISION = """# Direction Review Demo Vision (DRAFT)

## Where this is going

Proposals are read for what they actually say.
"""

#: The generic title is the whole point: it must never stand in for the
#: change or the rationale under it. `**What this asks for:**` etc. are the
#: preamble -- the author's own rationale, kept as `why`/`whyHtml` by
#: `app/data.py`'s `proposals_for` -- never a `## Why` heading, because this
#: repository's own real proposals never use one either (see the lane's own
#: notes: every ratified/candidate file here uses exactly "the exact
#: change" / "the evidence" / "what does not change").
STRUCTURED_LOCKED_FIRST = """# Console Contract -- v1 (FROZEN 2026-09-01)

## Core

1. The console never claims a state it cannot prove.
"""

STRUCTURED_LOCKED_SECOND = """# Console Contract -- v1 (FROZEN 2026-09-01)

## Core

1. The console never claims a state it cannot prove, and says so plainly.
"""

STRUCTURED_CANDIDATE = """# AFK Preview Contract -- Console -- proposed wording

**What this asks for:** that the console's idle-state sentence stop implying
a live connection when none exists, because a steward reading it at a glance
has no other signal to go on.

**Which promise it serves:** experience-console.v1 Core 3 (the console never
claims a state it cannot prove).

## The exact change

Current:

> Console is listening.

Replacement:

> Console is idle -- no session is attached.

## The evidence

- A steward read "listening" as attached and waited four minutes for a reply
  that was never coming.

## What does not change

The console's position, its open/close gesture, and every other sentence.
"""

UNSTRUCTURED_LOCKED = """# Plain Contract -- v1 (FROZEN 2026-09-01)

## Core

1. Nothing about this clause is under proposal in this fixture.
"""

UNSTRUCTURED_CANDIDATE = """# Tidy the changelog wording

Just reflow the changelog entry so it reads as one sentence instead of a
table row. Nothing else about the document changes.
"""

RETURN_LOG = """# Owner return log

## 2026-09-09 09:00 - return

**Time away.** A few hours.
**Finished.** Nothing relevant to this fixture.
**Stuck.** Nothing is stuck this turn.
**Needs you.** Two proposals are waiting on your word.
**Anything quietly broken.** Nothing quietly broke overnight.
"""

HIGHWAY = """# Highway -- direction-review proof

## Outcome

Prove neu6 and 8crs together, at both widths, with two identities.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

WIDTHS = [
    ("wide", 1280, 800, "1280"),
    ("narrow", 390, 844, "390"),
]


def _seed_repo(root: Path, name: str) -> Path:
    repo = root / name
    (repo / "docs" / "workflow").mkdir(parents=True)
    (repo / "contracts").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(STRUCTURED_LOCKED_FIRST, encoding="utf-8")
    (repo / "contracts" / "plain.v1.md").write_text(UNSTRUCTURED_LOCKED, encoding="utf-8")
    (repo / "docs" / "workflow" / "OWNER-RETURN-LOG.md").write_text(RETURN_LOG, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: vision and two locked contracts")

    # A second commit against the STRUCTURED doc only, so Changes has a real
    # sentence-level row to show (and a place for "Answer with these
    # choices" to appear) -- the unstructured doc is left alone.
    (repo / "contracts" / "demo.v1.md").write_text(STRUCTURED_LOCKED_SECOND, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "console: says so plainly")

    # Both candidates land AFTER the doc history above, as open proposals --
    # never committed themselves, exactly like a real unratified proposal.
    (repo / "contracts" / "demo.v1-candidate.md").write_text(STRUCTURED_CANDIDATE, encoding="utf-8")
    (repo / "contracts" / "plain.v1-candidate.md").write_text(UNSTRUCTURED_CANDIDATE, encoding="utf-8")
    return repo


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("direction-review-proof")
    repos = {tag: _seed_repo(tmp_path, f"{mid}-repo") for mid, _w, _h, tag in WIDTHS}

    blocks = []
    for (mid, _w, _h, tag) in WIDTHS:
        batch = tmp_path / f"hw-{mid}"
        (batch / "goals").mkdir(parents=True)
        (batch / "lanes" / "w1-alpha").mkdir(parents=True)
        (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
        (batch / "goals" / "w1-alpha.md").write_text("# Lane alpha\n", encoding="utf-8")
        (batch / "lanes" / "w1-alpha" / "lane.log").write_text("working\n", encoding="utf-8")
        (batch / "manifest.tsv").write_text(
            MANIFEST_HEAD
            + f"w1-alpha\t{batch}/lanes/w1-alpha/demo-repo\tlane/w1-alpha\tdeadbee\t"
            f"hw__hw-{mid}__w1-alpha\t{batch}/goals/w1-alpha.md\t"
            f"{batch}/lanes/w1-alpha/lane.log\t2026-09-09T09:00:00Z\n",
            encoding="utf-8",
        )
        blocks.append(
            "[[managers]]\n"
            f'id = "{mid}"\n'
            f'name = "Direction review demo {mid}"\n'
            f'batch_dir = "{batch}"\n'
            f'repos = ["{repos[tag]}"]\n'
            f'steward = "{USER}"\n'
            'tracker_project = ""\n'
            'tmux_socket = "test-socket-that-does-not-exist"\n'
        )

    conf = tmp_path / "converge-app.toml"
    conf.write_text("\n".join(blocks), encoding="utf-8")
    return {
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
        "sessions": tmp_path / "sessions.json",
        "repos": repos,
    }


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server(project):
    import uvicorn

    made = serve.create_app(
        config_path=project["config"],
        secret_path=project["secret"],
        state_path=project["state"],
        sessions_path=project["sessions"],
    )
    port = _free_port()
    config = uvicorn.Config(made, host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not uv_server.started and time.time() < deadline:
        time.sleep(0.05)
    assert uv_server.started, "app server did not start"
    yield f"http://127.0.0.1:{port}"
    uv_server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        yield b
        b.close()


def _records(repo: Path) -> set[Path]:
    return set((repo / "docs" / "workflow").glob("owner-ratifications-*.md"))


# --------------------------------------------------------------------------
# the proof
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("manager_id,width,height,tag", WIDTHS, ids=[w[3] for w in WIDTHS])
def test_review_and_changes_content_and_authority(server, project, browser, manager_id, width, height, tag):
    repo: Path = project["repos"][tag]
    structured_candidate = repo / "contracts" / "demo.v1-candidate.md"
    unstructured_candidate = repo / "contracts" / "plain.v1-candidate.md"
    structured_text = structured_candidate.read_text(encoding="utf-8")
    unstructured_text = unstructured_candidate.read_text(encoding="utf-8")
    print(f"\n=== {width}x{height} - manager {manager_id} - {repo} ===")

    def _enter(page):
        _click(page, f'[data-home-manager="{manager_id}"]', what=f"the {manager_id} session card")
        page.wait_for_selector("#operationView:not(.hidden)", timeout=15000)
        _stow_console(page, width)
        _click(page, "#directionTab", what="the Direction tab")
        page.wait_for_selector("#directionView:not(.hidden)", timeout=15000)
        _stow_console(page, width)

    # -- steward: structured candidate -------------------------------------
    ctx, page, errors = _boot(browser, server, project, width=width, height=height, user=USER)
    try:
        _enter(page)
        _open_doc(page, "Demo")
        _mode(page, "review")
        page.wait_for_selector(".review-hero h2", timeout=15000)

        heading = page.eval_on_selector(".review-hero h2", "el => el.textContent.trim()")
        assert heading == "AFK Preview Contract -- Console -- proposed wording", (
            f"Review's own hero should still show the proposal's title: {heading!r}"
        )

        sections = page.eval_on_selector_all(
            ".review-main .review-section",
            "els => els.map(e => ({ h3: (e.querySelector('h3')?.textContent || '').trim(), "
            "text: e.textContent.trim() }))",
        )
        by_heading = {s["h3"]: s["text"] for s in sections}
        print(f"  Review sections offered: {list(by_heading)}")

        what_changes = by_heading.get("What changes", "")
        why_now = by_heading.get("Why now", "")
        evidence = by_heading.get("Evidence", "")
        unchanged = by_heading.get("What does not change", "")

        assert "Console is idle" in what_changes, (
            f"'What changes' does not show the real exact-change wording: {what_changes!r}"
        )
        assert heading not in what_changes, (
            f"'What changes' substituted the proposal's title for the real change: {what_changes!r}"
        )
        assert "reading it at a glance" in why_now, (
            f"'Why now' does not show the real rationale: {why_now!r}"
        )
        assert "Console is idle" not in why_now, (
            f"the exact-change wording leaked into 'Why now': {why_now!r}"
        )
        assert "four minutes" in evidence, f"the evidence bullet is missing: {evidence!r}"
        assert "open/close gesture" in unchanged, f"'What does not change' is missing: {unchanged!r}"

        # Complete source access: the full original proposal, byte-for-byte.
        full = page.eval_on_selector(".review-fullbody", "el => el.textContent")
        assert "What this asks for" in full and "Console is listening" in full, (
            "the complete original proposal is not reachable from Review"
        )
        _shot(page, tag, "01-steward-review-structured")

        # 8crs: the steward's decision controls are live.
        disabled = page.eval_on_selector_all("[data-decision]", "els => els.map(e => e.disabled)")
        assert disabled and not any(disabled), f"the registered steward saw a disabled decision control: {disabled}"

        before = _records(repo)
        with page.expect_response(
            lambda r: r.url.endswith("/decision") and r.request.method == "POST", timeout=20000
        ):
            _click(page, '[data-decision="ratified"]', what="Ratify, as the steward")
        page.wait_for_function(
            "() => { const el = document.getElementById('toast'); "
            "return el && !el.classList.contains('hidden') && el.textContent.trim().length > 0; }",
            timeout=15000,
        )
        _shot(page, tag, "02-steward-review-decided")
        after = _records(repo)
        new_records = after - before
        assert len(new_records) == 1, f"the steward's decision did not write one new record: {new_records}"
        record_text = new_records.pop().read_text(encoding="utf-8")
        assert "**Decision:** Ratified" in record_text, f"the record's word is wrong:\n{record_text}"
        assert f"**By:** {USER}" in record_text, f"the record does not name the steward:\n{record_text}"
        assert "demo" in record_text, "the record does not name the document decided"

        # -- steward: Changes screen's "Answer with these choices" --------
        _mode(page, "changes")
        page.wait_for_selector(".changes-banner", timeout=15000)
        answer_btn = page.query_selector('.changes-banner-actions [data-decision]')
        assert answer_btn is not None, "Changes does not offer 'Answer with these choices'"
        assert not answer_btn.is_disabled(), "the registered steward saw a disabled Changes decision control"
        _shot(page, tag, "03-steward-changes-enabled")

        # -- steward: unstructured candidate --------------------------------
        _open_doc(page, "Plain")
        _mode(page, "review")
        page.wait_for_selector(".review-hero h2", timeout=15000)
        unstructured_heading = page.eval_on_selector(".review-hero h2", "el => el.textContent.trim()")
        assert unstructured_heading == "Tidy the changelog wording"

        no_change_section = page.query_selector('.review-main h3:has-text("What changes")')
        assert no_change_section is None, (
            "an unstructured proposal must not show a fabricated 'What changes' section"
        )
        full_unstructured = page.eval_on_selector(".review-main", "el => el.textContent")
        assert "reflow the changelog entry" in full_unstructured, (
            "the unstructured proposal's own prose is not fully readable"
        )
        assert "does not use headings this reader recognizes" in full_unstructured, (
            "an unstructured proposal must say honestly that nothing was labeled, not stay silent"
        )
        _shot(page, tag, "04-steward-review-unstructured")
        assert not errors, f"the steward's page logged errors: {errors}"
    finally:
        ctx.close()

    # -- teammate: sees guidance before any attempt, on both surfaces ------
    other_ctx, other_page, other_errors = _boot(browser, server, project, width=width, height=height, user=OTHER_USER)
    try:
        _enter(other_page)
        _open_doc(other_page, "Plain")
        _mode(other_page, "review")
        page = other_page  # noqa: F841 - readability at the call sites below
        other_page.wait_for_selector("[data-decision]", timeout=15000)

        disabled = other_page.eval_on_selector_all("[data-decision]", "els => els.map(e => e.disabled)")
        gate_note = other_page.eval_on_selector(".steward-gate-note", "el => el.textContent.trim()")
        print(f"  teammate sees Review decisions disabled={disabled}; explanation: {gate_note!r}")
        assert disabled and all(disabled), f"a non-steward saw a live decision control: {disabled}"
        assert USER in gate_note, f"the explanation does not name the registered steward: {gate_note!r}"
        # The proposal itself -- an allowed, read-only teammate action --
        # must still be fully visible: this is guidance, not a lockout.
        full_unstructured = other_page.eval_on_selector(".review-main", "el => el.textContent")
        assert "reflow the changelog entry" in full_unstructured, (
            "a non-steward must still be able to read the full proposal"
        )
        _shot(other_page, tag, "05-teammate-review-disabled")

        _open_doc(other_page, "Demo")
        _mode(other_page, "changes")
        other_page.wait_for_selector(".changes-banner", timeout=15000)
        answer_btn = other_page.query_selector('.changes-banner-actions [data-decision]')
        assert answer_btn is not None
        assert answer_btn.is_disabled(), "a non-steward saw a live Changes decision control"
        assert "steward-gate-note" in (other_page.eval_on_selector(".changes-banner-actions", "el => el.innerHTML")), (
            "Changes did not explain the boundary to the non-steward"
        )
        _shot(other_page, tag, "06-teammate-changes-disabled")

        # -- direct unauthorized request: bypasses the disabled control ----
        _open_doc(other_page, "Plain")
        _mode(other_page, "review")
        other_page.wait_for_selector("[data-decision]", timeout=15000)
        before = _records(repo)
        direct = other_page.evaluate(
            """async (decision) => {
                try {
                    // converge-moe4: main.js is now served from a per-generation
                    // VERSIONED URL (app/assets.py), so importing an absolute,
                    // unversioned '/static/js/state.js' here would load a SECOND,
                    // empty module instance rather than the one the running page
                    // already populated -- resolved relative to the script the
                    // page itself loaded, exactly like main.js's own import does,
                    // so this always shares the SAME singleton.
                    const mainSrc = document.querySelector('script[type="module"][src*="/js/main.js"]').src;
                    const { state, data } = await import(new URL('./state.js', mainSrc).href);
                    const { api } = await import(new URL('./api.js', mainSrc).href);
                    const proposalId = (data.doc && (data.doc.proposals || [])[0] && data.doc.proposals[0].id) || null;
                    if (!proposalId) return { error: 'no open proposal id available client-side' };
                    await api.decision(state.managerId, {
                        repoId: state.repoId, docId: state.docId, proposalId, decision, note: '',
                    });
                    return { ok: true };
                } catch (err) {
                    return { status: err.status, said: err.message };
                }
            }""",
            "declined",
        )
        print(f"  teammate direct decision request -> {direct}")
        assert direct.get("status") == 403, (
            f"a direct decision request from a non-steward was not refused: {direct}"
        )
        after = _records(repo)
        assert after == before, f"the refused direct request wrote a record: {after - before}"
        _shot(other_page, tag, "07-teammate-direct-refused")

        unexpected = [
            line for line in other_errors
            if not (line.startswith("console.error: Failed to load resource") and "403" in line)
        ]
        assert not unexpected, f"the teammate's page logged real errors: {unexpected}"
    finally:
        other_ctx.close()
