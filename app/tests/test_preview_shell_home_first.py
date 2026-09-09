"""Source-level fences for the shell-inbox preview lane (converge-t30q).

These check the same five acceptance items the goal names, but at the source
level rather than in a real browser -- this sandbox has no Playwright/Chromium
available (the manager's own baseline run shows 149 browser checks skipped for
that reason), so a rendered proof of these changes is NOT available here.
`app/tests/test_shell_home.py`, `test_console_live_rendered.py` and
`test_console_overflow_rendered.py` were updated in this same change to open a
manager session before exercising console/manager behaviour (boot no longer
does that automatically) and to force a known console open/closed state
before asserting a toggle direction; those files carry the real rendered
proof once Playwright is available, and their own docstrings/comments name
what changed and why.

This file is the source fence that DOES run everywhere: it reads the shipped
JS and asserts the exact shape converge-t30q asked for, so a later edit that
quietly reintroduces auto-selecting the first manager, a default-open
console, or the old jump-to-first-document needs pill is caught without a
browser at all.
"""

from __future__ import annotations

import re
from pathlib import Path

JS = Path(__file__).resolve().parents[1] / "static" / "js"

MAIN_JS = (JS / "main.js").read_text(encoding="utf-8")
STATE_JS = (JS / "state.js").read_text(encoding="utf-8")
ACTIONS_JS = (JS / "actions.js").read_text(encoding="utf-8")
HOME_JS = (JS / "render" / "home.js").read_text(encoding="utf-8")
CONSOLE_JS = (JS / "render" / "console.js").read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# acceptance 1 -- boot lands on Home, not an arbitrarily first-picked manager
# --------------------------------------------------------------------------


def test_boot_never_auto_selects_the_first_manager() -> None:
    assert "selectManager(data.managerList[0]" not in MAIN_JS, (
        "boot() must not open the first listed manager automatically -- Home is the "
        "landing screen regardless of how many managers are registered"
    )
    boot_body = MAIN_JS[MAIN_JS.index("async function boot()") :]
    assert re.search(r"state\.screen\s*=\s*'home'", boot_body), (
        "boot() must always set state.screen = 'home' before its final render"
    )


def test_boot_stores_the_scanned_workspace_config_for_homes_empty_state() -> None:
    assert "data.config = bootData.config" in MAIN_JS, (
        "boot() must carry /api/boot's config block (scanned workspaces, source, note) "
        "onto data.config so Home can show where it looked with zero managers"
    )


def test_home_renders_a_named_empty_setup_state_from_that_config() -> None:
    assert "emptySetupHtml" in HOME_JS, "Home needs a real empty-state renderer, not a blank grid"
    assert "cfg.workspaces" in HOME_JS or "cfg && cfg.workspaces" in HOME_JS, (
        "the empty state must read the actual scanned workspace roots, not invent one"
    )
    assert "No workspace roots are configured to scan at all" in HOME_JS, (
        "an empty roots list needs its own explicit remedy sentence, not a silent blank list"
    )


def test_a_failed_manager_open_does_not_commit_the_new_id_before_the_read_lands() -> None:
    """converge-t30q acceptance 1: a failed fetch never mixes old content with a new title."""
    fn = MAIN_JS[MAIN_JS.index("export async function selectManager") :]
    fn = fn[: fn.index("\nexport async function selectDoc")]
    fetch_line = fn.index("await Promise.all([api.manager(id), api.operation(id)])")
    commit_line = fn.index("state.managerId = id;")
    assert fetch_line < commit_line, (
        "selectManager must fetch the new manager's data BEFORE writing state.managerId/"
        "state.screen -- otherwise a failed fetch leaves the new id showing over the old "
        "manager's content"
    )
    # And the failure path must return without having reached that commit line.
    catch_clause = fn[fetch_line : fn.index("state.managerId = id;")]
    assert "catch (err)" in catch_clause and "return;" in catch_clause


def test_opening_a_manager_defaults_to_operation_not_direction() -> None:
    fn = MAIN_JS[MAIN_JS.index("export async function selectManager") :]
    fn = fn[: fn.index("\nexport async function selectDoc")]
    assert "state.workspace = 'operation'" in fn, (
        "experience.v1 Core 1/2: opening a manager opens its Operation, with Direction "
        "an obvious peer tab away"
    )


# --------------------------------------------------------------------------
# acceptance 3 -- console starts closed and off Home's working area
# --------------------------------------------------------------------------


def test_console_defaults_closed() -> None:
    assert re.search(r"consoleOpen\s*:\s*false\s*,", STATE_JS), (
        "the console must start closed -- experience-console.v1 Core 1/7 keeps it out of "
        "Home's own working area until the steward opens it"
    )


def test_console_title_reads_a_human_manager_name_not_a_raw_id() -> None:
    assert "manager-${state.managerId}" not in CONSOLE_JS, (
        "the console header must not fall back to the machine id as its whole label"
    )
    assert "managerName" in CONSOLE_JS


# --------------------------------------------------------------------------
# acceptance 4 -- the needs pill opens a dialog of at most five named choices
# --------------------------------------------------------------------------


def test_needs_pill_opens_a_dialog_instead_of_jumping_to_the_first_document() -> None:
    assert "openNeeds" in MAIN_JS, "wire() must call the shell's own needs dialog"
    assert "async () => {" not in MAIN_JS.split("on('needsYouButton'")[1].split(");")[0], (
        "the needs pill's own inline jump-to-first-document handler must be gone"
    )


def test_needs_dialog_caps_at_five_and_names_each_choice() -> None:
    fn = ACTIONS_JS[ACTIONS_JS.index("export async function openNeeds") :]
    fn = fn[: fn.index("\nexport function openSteer")]
    assert ".slice(0, 5)" in fn, "at most five things ask for a word at once (experience.v1 Core 5)"
    assert "needKindLabel" in fn and "needTargetLabel" in fn, (
        "each row must name its own kind and its own target, not a bare title"
    )


def test_needs_dialog_gives_a_non_document_item_an_honest_path_not_a_review_tab() -> None:
    """Manager correction 2 (converge-t30q): Console-only was itself the defect.

    A work-tracker item still gets no document view -- that part of the
    original fence stands -- but the honest path is Operation's own existing
    controls (queue/priority/feedback/steer), with the Console left exactly
    as the steward last had it, never forced open as the only answer.
    """
    fn = ACTIONS_JS[ACTIONS_JS.index("export async function openNeeds") :]
    fn = fn[: fn.index("\nexport function openSteer")]
    assert "docMode = 'review'" in fn, "a proposal still opens the ordinary review path"
    assert "no document view" in fn, (
        "a work-tracker item must say plainly that this app has no document view for it, "
        "rather than routing it into Review anyway"
    )
    assert "state.workspace = 'operation'" in fn, (
        "a non-document need must land on Operation, where its existing queue/priority/"
        "feedback/steer controls already answer it"
    )
    assert "state.consoleOpen = true" not in fn, (
        "the Console must not be forced open as the ONLY answer for a non-document need -- "
        "it stays optional, exactly as the steward left it"
    )


# --------------------------------------------------------------------------
# acceptance 5 -- listeners are guarded, PWA principal is awaited
# --------------------------------------------------------------------------


def test_wire_guards_every_listener_against_a_removed_element() -> None:
    wire_fn = MAIN_JS[MAIN_JS.index("function wire() {") : MAIN_JS.index("\nasync function boot()")]
    # Every single-element wire-up goes through on(id, event, handler); a bare
    # `$('id').addEventListener(` reintroduces the boot-time TypeError a
    # removed reader-owned element used to cause.
    bare = re.findall(r"\$\('[^']+'\)\.addEventListener\(", wire_fn)
    assert not bare, f"found un-guarded listener(s) in wire(): {bare}"
    assert wire_fn.count("on(") >= 20, "wire() should route its per-id listeners through on(...)"


def test_boot_awaits_the_pwa_principal_before_any_manager_read() -> None:
    boot_body = MAIN_JS[MAIN_JS.index("async function boot()") :]
    principal_at = boot_body.index("ConvergePWA.setPrincipal")
    manager_list_at = boot_body.index("data.managerList = bootData.managers")
    assert principal_at < manager_list_at, (
        "setPrincipal must be awaited before this session reads manager data, per "
        "preview-common.md's shared-interfaces section"
    )
    assert "await window.ConvergePWA.setPrincipal" in boot_body


def test_feedback_from_home_never_silently_picks_a_manager() -> None:
    """Manager correction 4 (converge-t30q): the old silent fallback was the defect.

    Home-first boot means `state.managerId` can be null when Feedback is
    opened from Home (converge-nng's control is reachable there); the fix is
    not to guess a target from the first listed manager, but to ask -- an
    explicit chooser -- before the write can be sent.
    """
    target_fn = ACTIONS_JS[ACTIONS_JS.index("function feedbackTargetId") :]
    target_fn = target_fn[: target_fn.index("\nexport function openFeedback")]
    assert "data.managerList" not in target_fn, (
        "feedbackTargetId must not fall back to the manager list at all -- it answers only "
        "the manager already open, or nothing"
    )
    open_fn = ACTIONS_JS[ACTIONS_JS.index("export function openFeedback") :]
    open_fn = open_fn[: open_fn.index("\n// ---") if "\n// ---" in open_fn else len(open_fn)]
    assert "feedbackTarget" in open_fn, (
        "with no manager open, openFeedback must offer an explicit recipient chooser"
    )
    assert "needsChooser" in open_fn
    assert "api.feedback(targetId" in ACTIONS_JS
