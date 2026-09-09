"""CVG-106: `ledger/checks/project_state.py`, exercised against real code.

Every test here runs the PRODUCTION probe against either this repository's
own `app/` (unchanged) or a disposable COPY of it with one thing mutated --
never a self-authored payload standing in for the real writers. That is the
falsifier named in the row: a probe that only proves auth.py is on a
whitelist would pass even if its schema silently grew a fourth key; the
tests below mutate the actual generated artifact's shape, not the writer
list, to prove that is not what is happening.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "ledger" / "checks"))

from project_state import evaluate  # noqa: E402


@pytest.fixture
def mutated_app(tmp_path: Path) -> Path:
    """A disposable copy of this repository's real `app/` directory, so a
    test can mutate one file's production code and run the real probe
    against it -- without ever touching the checkout itself."""
    root = tmp_path / "project"
    shutil.copytree(REPO_ROOT / "app", root / "app")
    return root


# ---------------------------------------------------------------------------
# 1. the unchanged, real, current production state
# ---------------------------------------------------------------------------


def test_the_real_unmodified_app_passes():
    """Acceptance #1: the unchanged contract's legitimate current production
    state passes a probe that actually exercises code."""
    result = evaluate(REPO_ROOT)
    assert result.passed, result.reason
    # It genuinely ran something, for each of the five known writers -- not
    # a hollow verdict with nothing behind it.
    labels = {line.split(":", 1)[0] for line in result.checked}
    assert labels == {"auth.py", "feedback_voice.py", "state_store.py", "tls.py", "writes.py"}


def test_a_tree_with_no_app_directory_is_reviewed_not_passed(tmp_path: Path):
    result = evaluate(tmp_path)
    assert not result.passed
    assert "no app/ directory" in result.reason


# ---------------------------------------------------------------------------
# 2. negative control: a new, unclassified external writer
# ---------------------------------------------------------------------------


def test_a_new_writer_module_is_reviewed_not_silently_passed(mutated_app: Path):
    (mutated_app / "app" / "rogue_writer.py").write_text(
        "from pathlib import Path\n\n\ndef leak() -> None:\n    Path('/tmp/rogue-cvg106.txt').write_text('x')\n",
        encoding="utf-8",
    )
    result = evaluate(mutated_app)
    assert not result.passed
    assert "rogue_writer.py" in result.reason
    assert "new writer" in result.reason

    # positive control: remove the rogue file, the same tree passes again.
    (mutated_app / "app" / "rogue_writer.py").unlink()
    restored = evaluate(mutated_app)
    assert restored.passed, restored.reason


# ---------------------------------------------------------------------------
# 3. negative control: a known writer's write disappears (the set shrinks)
# ---------------------------------------------------------------------------


def test_a_known_writer_losing_its_write_is_reviewed(mutated_app: Path):
    tls_path = mutated_app / "app" / "tls.py"
    original = tls_path.read_text(encoding="utf-8")
    tls_path.write_text('"""stubbed out for a test: no write left in this file."""\n', encoding="utf-8")

    result = evaluate(mutated_app)
    assert not result.passed
    assert "tls.py" in result.reason
    assert "gone" in result.reason

    # positive control
    tls_path.write_text(original, encoding="utf-8")
    restored = evaluate(mutated_app)
    assert restored.passed, restored.reason


# ---------------------------------------------------------------------------
# 4. negative control: the reading store grows a third, project-truth field
# ---------------------------------------------------------------------------


def test_a_third_reading_store_field_is_reviewed(mutated_app: Path):
    """This is the false-positive `verify.py` would never have caught by
    counting writer files: the writer set is unchanged, only the SCHEMA of
    what `state_store.py` persists grows a project-truth-shaped key."""
    path = mutated_app / "app" / "state_store.py"
    original = path.read_text(encoding="utf-8")
    mutated = original.replace(
        'mine.setdefault("read", {})\n        mine.setdefault("kept", {})',
        'mine.setdefault("read", {})\n        mine.setdefault("kept", {})\n        mine.setdefault("documents", {})',
    )
    assert mutated != original, "the fixture's replace target no longer matches state_store.py -- update it"
    path.write_text(mutated, encoding="utf-8")

    result = evaluate(mutated_app)
    assert not result.passed
    assert "documents" in result.reason or "read" in result.reason

    # positive control
    path.write_text(original, encoding="utf-8")
    restored = evaluate(mutated_app)
    assert restored.passed, restored.reason


# ---------------------------------------------------------------------------
# 5. negative control: a repository writer's target escapes the given repo
# ---------------------------------------------------------------------------


def test_a_repository_write_escaping_the_repo_is_reviewed(mutated_app: Path):
    path = mutated_app / "app" / "writes.py"
    original = path.read_text(encoding="utf-8")
    mutated = original.replace(
        'folder = Path(repo) / ".converge" / "feedback"',
        'folder = Path(repo).parent / "escaped-feedback"',
        1,
    )
    assert mutated != original, "the fixture's replace target no longer matches writes.py -- update it"
    path.write_text(mutated, encoding="utf-8")

    result = evaluate(mutated_app)
    assert not result.passed
    assert "outside the repository" in result.reason

    # positive control
    path.write_text(original, encoding="utf-8")
    restored = evaluate(mutated_app)
    assert restored.passed, restored.reason


# ---------------------------------------------------------------------------
# 6a. negative control: a signing token wrong in shape, not merely "is JSON"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("replacement", "reason"),
    [
        ("made = secrets.token_urlsafe(16)", "chars long"),
        ('made = "!" * 64', "alphabet"),
    ],
    ids=["wrong-length", "invalid-alphabet"],
)
def test_a_malformed_signing_token_is_reviewed(mutated_app: Path, replacement: str, reason: str):
    """Length and alphabet each have a negative and restored positive control."""
    path = mutated_app / "app" / "auth.py"
    original = path.read_text(encoding="utf-8")
    mutated = original.replace("made = secrets.token_urlsafe(48)", replacement, 1)
    assert mutated != original, "the fixture's replace target no longer matches auth.py -- update it"
    path.write_text(mutated, encoding="utf-8")

    result = evaluate(mutated_app)
    assert not result.passed
    assert "auth.py" in result.reason
    assert reason in result.reason

    # positive control
    path.write_text(original, encoding="utf-8")
    restored = evaluate(mutated_app)
    assert restored.passed, restored.reason


# ---------------------------------------------------------------------------
# 6b. negative control: TLS material that is not a real, bare PEM object
# ---------------------------------------------------------------------------


def _replace_second_occurrence(text: str, target: str, replacement: str) -> str:
    """Replace only the SECOND occurrence of `target` in `text`.

    Used below to mutate `_make_leaf`'s return statement without touching
    `_make_ca`'s identical-looking one (the first occurrence): the CA's
    cert/key bytes are read back and re-parsed internally by `ensure()`
    while signing the leaf, so breaking the CA would fail inside the
    production code's own certificate generation rather than exercising
    this probe's check -- the leaf's returned bytes are only ever written
    to disk, never re-parsed by `ensure()` afterwards, so mutating them is
    the clean way to hand the probe a bad *artifact* rather than a
    production crash.
    """
    first, sep, rest = text.partition(target)
    assert sep, f"target {target!r} not found at all"
    second_index = rest.find(target)
    assert second_index != -1, f"target {target!r} found only once, expected twice"
    return first + sep + rest[:second_index] + replacement + rest[second_index + len(target) :]


def test_garbage_wrapped_in_pem_markers_is_reviewed(mutated_app: Path):
    """The retired check only asked whether the substring `-----BEGIN`
    appeared anywhere in the file -- garbage between real-looking BEGIN/END
    markers passed it. It must not parse as a real certificate now."""
    path = mutated_app / "app" / "tls.py"
    original = path.read_text(encoding="utf-8")
    target = "    return key_bytes, cert.public_bytes(serialization.Encoding.PEM)"
    replacement = (
        '    return key_bytes, b"-----BEGIN CERTIFICATE-----\\nbm90LXJlYWwtY2VydC1kYXRh\\n-----END CERTIFICATE-----\\n"'
    )
    mutated = _replace_second_occurrence(original, target, replacement)
    assert mutated != original, "the fixture's replace target no longer matches tls.py -- update it"
    path.write_text(mutated, encoding="utf-8")

    result = evaluate(mutated_app)
    assert not result.passed
    assert "leaf_cert" in result.reason
    assert "does not parse" in result.reason

    # positive control
    path.write_text(original, encoding="utf-8")
    restored = evaluate(mutated_app)
    assert restored.passed, restored.reason


def test_a_real_pem_with_copied_text_appended_is_reviewed(mutated_app: Path):
    """The acceptance's own falsifier, named directly: a real PEM certificate
    that ALSO carries appended text (here, something project-record-shaped)
    must not pass just because the certificate part of it is genuine."""
    path = mutated_app / "app" / "tls.py"
    original = path.read_text(encoding="utf-8")
    target = "    return key_bytes, cert.public_bytes(serialization.Encoding.PEM)"
    replacement = target + ' + b\'\\n{"decisions": ["copied project record"]}\\n\''
    mutated = _replace_second_occurrence(original, target, replacement)
    assert mutated != original, "the fixture's replace target no longer matches tls.py -- update it"
    path.write_text(mutated, encoding="utf-8")

    result = evaluate(mutated_app)
    assert not result.passed
    assert "leaf_cert" in result.reason
    assert "appended after the PEM block" in result.reason

    # positive control
    path.write_text(original, encoding="utf-8")
    restored = evaluate(mutated_app)
    assert restored.passed, restored.reason


# ---------------------------------------------------------------------------
# 6c. negative control: a copied field riding inside a nested read entry
# ---------------------------------------------------------------------------


def test_a_copied_field_inside_a_read_entry_is_reviewed(mutated_app: Path):
    """The top-level-only check (`set(mine.keys()) == {"read", "kept"}`)
    would pass this silently: the two top-level names are unchanged, only
    ONE read entry grows a third, project-record-shaped field (the document
    name, copied in alongside the commit pointer and timestamp it is allowed
    to carry)."""
    path = mutated_app / "app" / "state_store.py"
    original = path.read_text(encoding="utf-8")
    mutated = original.replace(
        'mine["read"][self.key(repo, doc)] = {"sha": sha, "at": _stamp()}',
        'mine["read"][self.key(repo, doc)] = {"sha": sha, "at": _stamp(), "doc": doc}',
        1,
    )
    assert mutated != original, "the fixture's replace target no longer matches state_store.py -- update it"
    path.write_text(mutated, encoding="utf-8")

    result = evaluate(mutated_app)
    assert not result.passed
    assert "read entry" in result.reason
    assert "not exactly sha and at" in result.reason

    # positive control
    path.write_text(original, encoding="utf-8")
    restored = evaluate(mutated_app)
    assert restored.passed, restored.reason


# ---------------------------------------------------------------------------
# 7. instance-security state is never mistaken for a copied project record
# ---------------------------------------------------------------------------


def test_signing_secret_and_revocation_table_are_not_project_truth():
    """Directly names what acceptance #1 depends on: the two auth.py
    artifacts are proved by shape, not merely allowed by filename."""
    result = evaluate(REPO_ROOT)
    assert result.passed, result.reason
    auth_lines = [line for line in result.checked if line.startswith("auth.py:")]
    assert len(auth_lines) == 2
    assert any("opaque token" in line for line in auth_lines)
    assert any("revoked session ids" in line for line in auth_lines)


def test_tls_material_is_classified_explicitly_not_silently_skipped():
    """The retired probe's regex never matched `app/tls.py`'s write at all
    -- this pins that the current probe both SEES it and classifies it."""
    result = evaluate(REPO_ROOT)
    assert result.passed, result.reason
    assert any(line.startswith("tls.py:") for line in result.checked)
