#!/usr/bin/env python3
"""CVG-106: does the app hold no copy of the project's truth?

`experience.v1` Core 7 says the app "holds no copy of the project's truth" --
it shows documents, code record, work queue, lanes, return log and pending
decisions, and keeps none of them. A second copy of the truth is a defect,
"not a cache." The clause does NOT say a module may never write a file.

The probe this file replaces read that prohibition backwards: it counted
writer MODULES (three named files, a fourth is red) rather than watching
what gets WRITTEN. That miscounted `app/auth.py`'s signing secret and
session-revocation table, and (unseen by either probe, old or new, until
now) `app/tls.py`'s local CA and leaf certificate/key, as violations. None
of the four are a copied project record -- they are per-instance security
state, which Core 7's own ratified text (`experience.v1-candidate`, applied
2026-09-06) explicitly carves out: "Your own reading ... is yours, kept per
person outside the repository." A signing secret and a revoked-session list
are narrower than that: they are not even the STEWARD's data, they belong to
this one running instance and would be meaningless copied anywhere else.

So this probe classifies, per module, WHAT is written and checks the
SCHEMA of the artifact against what that classification allows -- not
merely that the writer's name is on a list:

  * `app/writes.py`, `app/feedback_voice.py`     -- REPOSITORY. Must land
    inside the steward's own repository (the project's truth already lives
    there; a commit is how it is kept). A write that escapes the given repo
    path is the actual defect Core 7 is about.
  * `app/state_store.py`                          -- READING STORE. Per
    steward, exactly a read point and kept marks -- nothing else. A third
    key is a second copy of the truth arriving by a side door.
  * `app/auth.py`, `app/tls.py`                    -- INSTANCE SECURITY.
    A signing secret (opaque token), a session-revocation list (session ids
    only) and a local CA/leaf (PEM cert + key material) -- proved by
    inspecting what each one actually generates, not merely trusted because
    its name is allowed.

A module discovered writing to disk that carries NONE of the three labels
above is unclassified, and unclassified is REVIEW, never a silent PASS --
same as a classified module whose OWN artifact stops matching its schema.

WHAT THIS DOES NOT PROVE, named so it is not read as more: that every value
the app shows on screen is read back from the project (that is
`app/README.md`'s source-by-source table, unchecked by anything here). Nor
does it defend against a module that writes through some indirection this
probe's bounded regex does not recognise (see `WRITE_SIGNATURE`) -- this is
a small, named inventory, not a general static-analysis framework.
"""

from __future__ import annotations

import json
import re
import secrets
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Callable

from cryptography import x509
from cryptography.hazmat.primitives import serialization

# ---------------------------------------------------------------------------
# the bounded writer inventory
# ---------------------------------------------------------------------------

#: Every app/*.py file allowed to persist anything to disk at all, and the
#: label naming what it is trusted to persist. Anything else is REVIEW.
KNOWN_WRITERS: dict[str, str] = {
    "writes.py": "repository",
    "feedback_voice.py": "repository",
    "state_store.py": "reading_store",
    "auth.py": "instance_security",
    "tls.py": "instance_security",
}

#: Any of these on a line means "this file persists something to disk".
#: Deliberately wider than the pattern the retired probe used
#: (`\.write_text\(|json\.dump\(`), which never matched `app/tls.py`'s
#: `os.open(..., O_CREAT ...)` + `fdopen(..., "wb")` + `.write(data)` --
#: so a fourth writer went unclassified rather than merely mis-classified.
WRITE_SIGNATURE = re.compile(
    r"\.write_text\(|\.write_bytes\(|json\.dump\(|os\.open\([^)]*O_CREAT"
)


@dataclass
class ProbeResult:
    """PASS or REVIEW, with a concise, non-secret reason and what was
    actually checked -- never a raw secret, cert key, or session id."""

    verdict: str  # "PASS" | "REVIEW"
    reason: str
    checked: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"


def _review(reason: str, checked: list[str] | None = None) -> ProbeResult:
    return ProbeResult("REVIEW", reason, checked or [])


def _pass(reason: str, checked: list[str]) -> ProbeResult:
    return ProbeResult("PASS", reason, checked)


def _app_dir(root: Path) -> Path:
    return Path(root) / "app"


def discover_writers(root: Path) -> list[str]:
    """Every top-level `app/*.py` file (never `app/tests/`) whose source
    contains a file-write call, sorted by name.

    Sorted and compared for EXACT equality against `KNOWN_WRITERS`, not a
    subset check: a new writer appearing, or one of the known five
    disappearing, must be visible either direction -- the set is the
    tripwire, not merely its growth.
    """
    app_dir = _app_dir(root)
    if not app_dir.is_dir():
        return []
    return sorted(
        path.name for path in app_dir.glob("*.py") if WRITE_SIGNATURE.search(path.read_text(encoding="utf-8"))
    )


def _load(root: Path, filename: str) -> ModuleType:
    """The PRODUCTION module at `app/<filename>`, loaded fresh under a
    unique throwaway name so two calls against two different `root`s (the
    real tree, and a mutated fixture in a test) never collide through
    `sys.modules` caching.

    Reads the source text and `compile()`s it directly rather than handing
    the path to `spec_from_file_location`'s default `SourceFileLoader`:
    that loader validates its `__pycache__` bytecode cache by
    (mtime, size), and a test that mutates a file to the SAME byte length
    at a write speed finer than the filesystem's mtime resolution -- e.g.
    `token_urlsafe(48)` to `token_urlsafe(16)`, two characters either way --
    can leave it holding a stale compiled version of the file it just
    rewrote, silently. Compiling the just-read text has no such cache to
    go stale: every call sees exactly the bytes on disk at the moment it
    was called, never a previous call's compiled artifact.
    """
    path = _app_dir(root) / filename
    source = path.read_text(encoding="utf-8")
    unique = f"_cvg106_probe_{path.stem}_{uuid.uuid4().hex[:8]}"
    module = ModuleType(unique)
    module.__file__ = str(path)
    code = compile(source, str(path), "exec")
    sys.modules[unique] = module
    try:
        exec(code, module.__dict__)
    finally:
        sys.modules.pop(unique, None)
    return module


# ---------------------------------------------------------------------------
# schema checks -- one per writer module, run against the PRODUCTION code
# with an isolated, disposable path. Each returns (ok, detail-or-reason).
# ---------------------------------------------------------------------------


def _check_reading_store(root: Path, scratch: Path) -> tuple[bool, str]:
    """Exercises the real `Store` against an isolated path. Reads back the
    generated JSON's SCHEMA -- not the source that decided it -- so a third
    per-steward key arriving by any code path is caught, not just the one
    line the retired probe counted.

    Checks the NESTED shape too, not only the two top-level names: a `read`
    entry must be exactly `{"sha": ..., "at": ...}` (both strings) -- a copied
    project-record field (a document title, a lane name, anything beyond the
    commit pointer and the timestamp) riding along inside that dict would
    pass the old top-level-only check silently. A `kept` entry must be a
    list of plain strings -- nothing structured smuggled in as a "change".
    """
    module = _load(root, "state_store.py")
    path = scratch / "state.json"
    store = module.Store(path=path)
    store.set_read_point("steward-a", "repo", "doc", "deadbeef")
    store.keep("steward-a", "repo", "doc", "change-1")
    whole = json.loads(path.read_text(encoding="utf-8"))
    if set(whole.keys()) != {"stewards"}:
        return False, f"reading store's top level is {sorted(whole.keys())}, not just ['stewards']"
    mine = whole["stewards"].get("steward-a", {})
    if set(mine.keys()) != {"read", "kept"}:
        return False, f"steward-a's entry holds {sorted(mine.keys())}, not exactly a read point and kept marks"

    read_entries = mine["read"]
    if not isinstance(read_entries, dict):
        return False, f"read holds a {type(read_entries).__name__}, not a mapping of doc key -> read point"
    for doc_key, entry in read_entries.items():
        if not isinstance(entry, dict) or set(entry.keys()) != {"sha", "at"}:
            shape = sorted(entry.keys()) if isinstance(entry, dict) else type(entry).__name__
            return False, f"read entry {doc_key!r} holds {shape}, not exactly sha and at"
        if not isinstance(entry["sha"], str) or not isinstance(entry["at"], str):
            return False, f"read entry {doc_key!r}'s sha/at are not both strings"

    kept_entries = mine["kept"]
    if not isinstance(kept_entries, dict):
        return False, f"kept holds a {type(kept_entries).__name__}, not a mapping of doc key -> kept marks"
    for doc_key, marks in kept_entries.items():
        if not isinstance(marks, list) or not all(isinstance(mark, str) for mark in marks):
            return False, f"kept entry {doc_key!r} holds something other than a list of plain strings"

    return True, "reading store holds exactly a read point (sha, at) and kept-mark string lists, per steward"


def _check_signing_secret(root: Path, scratch: Path) -> tuple[bool, str]:
    """A signing secret is an opaque token, never structured data -- if it
    ever parsed as JSON holding project-shaped keys, that would be a second
    copy of the truth wearing a secret's clothes.

    Beyond "not JSON": `app/auth.py::read_or_make_secret` generates the
    secret with `secrets.token_urlsafe(48)` -- a URL-safe-base64 alphabet,
    fixed-length token, never logged or echoed here. This checks the actual
    generated artifact against THAT encoding (`[A-Za-z0-9_-]` only) and
    THAT length (`len(secrets.token_urlsafe(48))`, deterministic for a given
    byte count, itself derived from the stdlib call auth.py uses -- not an
    invented number), so a signing token the retired check would have waved
    through on "one non-JSON line" -- too short, or carrying a character the
    real generator never produces -- is caught. Never logs the token text
    itself in a failure message, only its length and whether it matched.
    """
    module = _load(root, "auth.py")
    path = scratch / "secret"
    made = module.read_or_make_secret(path=path)
    text = path.read_text(encoding="utf-8").strip()
    if text != made:
        return False, "the secret file's content does not match what read_or_make_secret returned"
    try:
        json.loads(text)
    except ValueError:
        pass
    else:
        return False, "the signing secret parses as structured JSON -- not what a bare token looks like"
    if len(text.splitlines()) != 1:
        return False, "the signing secret is not a single opaque token"
    if not re.fullmatch(r"[A-Za-z0-9_-]+", text):
        return False, "the signing secret contains a character outside token_urlsafe's alphabet"
    expected_length = len(secrets.token_urlsafe(48))  # same nbytes auth.py calls; length is deterministic
    if len(text) != expected_length:
        return False, f"the signing secret is {len(text)} chars long, not the {expected_length} token_urlsafe(48) always produces"
    return True, "signing secret is one opaque token_urlsafe(48)-shaped token, never structured data"


def _check_session_revocation(root: Path, scratch: Path) -> tuple[bool, str]:
    """A revocation table is a bare list of session ids -- nothing else."""
    module = _load(root, "auth.py")
    path = scratch / "sessions.json"
    registry = module.SessionRegistry(path=path)
    registry.revoke("test-sid-1")
    table = json.loads(path.read_text(encoding="utf-8"))
    if set(table.keys()) != {"revoked"}:
        return False, f"session registry's top level is {sorted(table.keys())}, not just ['revoked']"
    revoked = table["revoked"]
    if not isinstance(revoked, list) or not all(isinstance(item, str) for item in revoked):
        return False, "the revoked list holds something other than session-id strings"
    return True, "session registry holds exactly a list of revoked session ids"


#: One well-formed `-----BEGIN ...-----`...`-----END ...-----` block, greedy
#: only within a single BEGIN/END pair (`[^-]+` inside the label, `.*?` for
#: the body, non-greedy, so a second block later in the same text is never
#: swallowed into the first match).
_PEM_BLOCK = re.compile(r"-----BEGIN [^-]+-----.*?-----END [^-]+-----\s*", re.DOTALL)


def _single_pem_block(text: str) -> tuple[bool, str]:
    """(ok, reason). Fails on anything but exactly one well-formed PEM block
    spanning the whole file -- catches both "isn't PEM at all" and the
    negative control this row's evidence names directly: a real PEM object
    with project-record text copied in after it. The retired check only
    asked whether the substring `-----BEGIN` appeared anywhere, which both
    of those pass."""
    begins = text.count("-----BEGIN ")
    if begins != 1:
        return False, f"expected exactly one PEM block, found {begins}"
    match = _PEM_BLOCK.search(text)
    if match is None:
        return False, "no well-formed PEM block found"
    if match.start() != 0:
        return False, "content precedes the PEM block"
    if text[match.end() :].strip():
        return False, "content appended after the PEM block -- not a bare certificate/key"
    return True, ""


def _check_tls_material(root: Path, scratch: Path) -> tuple[bool, str]:
    """The local CA and leaf are certificate/key material (PEM), never a
    project record -- and never silently skipped the way the retired probe's
    regex skipped them (it never matched `tls.py`'s raw `os.open`+`fdopen`
    write at all).

    Beyond "the substring '-----BEGIN' appears": each file must be exactly
    one PEM block (see `_single_pem_block` -- catches a real certificate
    with project text appended after it, which the retired substring check
    would have passed), and it must actually PARSE as the kind of object it
    claims to be, via `cryptography` (already a dependency of `app/tls.py`
    itself -- no new package): `x509.load_pem_x509_certificate` for the two
    `*_cert` files, `serialization.load_pem_private_key` for the two `*_key`
    files. Garbage wrapped in real-looking BEGIN/END markers has the
    substring the old check wanted and fails to parse -- REVIEW, not PASS.
    """
    module = _load(root, "tls.py")
    made = module.ensure(tls_dir=scratch / "tls", extra_host="127.0.0.1")
    for label, path, kind in (
        ("ca_cert", made.ca_cert, "cert"),
        ("ca_key", made.ca_key, "key"),
        ("leaf_cert", made.leaf_cert, "cert"),
        ("leaf_key", made.leaf_key, "key"),
    ):
        text = path.read_text(encoding="utf-8")
        ok, reason = _single_pem_block(text)
        if not ok:
            return False, f"{label}: {reason}"
        try:
            if kind == "cert":
                x509.load_pem_x509_certificate(text.encode("utf-8"))
            else:
                serialization.load_pem_private_key(text.encode("utf-8"), password=None)
        except Exception:  # parser details may contain material being checked
            return False, f"{label} does not parse as a real PEM {kind}"
        try:
            json.loads(text)
        except ValueError:
            pass
        else:
            return False, f"{label} parses as JSON -- TLS material should never look like a project record"
    return True, "TLS material (CA + leaf, cert + key) is exactly one real, parseable PEM object each, never project data"


def _check_repository_write_stays_inside_repo(root: Path, scratch: Path) -> tuple[bool, str]:
    """`record_feedback` must land inside the caller's OWN repository -- the
    project's truth already lives there, so this is a normal commit-bound
    write, not a second copy of it living somewhere the app controls."""
    module = _load(root, "writes.py")
    repo = scratch / "repo"
    repo.mkdir()
    result = module.record_feedback(repo, text="a probe note")
    written = Path(result["path"])
    try:
        written.relative_to(repo)
    except ValueError:
        return False, f"feedback landed at {written}, outside the repository it was given"
    if ".converge" not in written.parts or "feedback" not in written.parts:
        return False, f"feedback did not land under .converge/feedback: {written}"
    return True, "feedback lands inside the caller's own repository, under .converge/feedback"


def _check_voice_note_target_is_repo_scoped(root: Path, scratch: Path) -> tuple[bool, str]:
    """RESIDUAL, named rather than hidden: `feedback_voice.py`'s write lives
    inside an async route handler bound to a live `Request` (manager lookup,
    `await request.json()`), which needs a mounted app and a PAM sign-in to
    exercise end to end (see `app/tests/test_feedback_voice.py`) -- more than
    this bounded probe carries. What IS checked, directly against the
    source: its write target is built from the exact same repository-
    relative literal `record_feedback` uses, never a path of the app's own.
    This is a static check of the target expression, not an observed write.
    """
    del scratch  # unused; the check reads source, it does not execute code
    text = (root / "app" / "feedback_voice.py").read_text(encoding="utf-8")
    if re.search(r'Path\(repo\)\s*/\s*"\.converge"\s*/\s*"feedback"', text) is None:
        return False, "feedback_voice.py no longer writes under the caller's repo at .converge/feedback"
    return True, (
        "feedback_voice.py's write target is Path(repo)/.converge/feedback, the same "
        "repository-relative literal record_feedback uses (static check -- see the residual note)"
    )


FILE_CHECKS: dict[str, list[Callable[[Path, Path], tuple[bool, str]]]] = {
    "state_store.py": [_check_reading_store],
    "auth.py": [_check_signing_secret, _check_session_revocation],
    "tls.py": [_check_tls_material],
    "writes.py": [_check_repository_write_stays_inside_repo],
    "feedback_voice.py": [_check_voice_note_target_is_repo_scoped],
}


def evaluate(root: str | Path) -> ProbeResult:
    """PASS or REVIEW for the app rooted at `root` (a real checkout, or a
    mutated fixture in a test). Never raises on an ordinary classification
    failure -- that is a REVIEW, reported with its concise reason."""
    root = Path(root)
    if not _app_dir(root).is_dir():
        return _review(f"no app/ directory found under {root}")

    writers = discover_writers(root)
    expected = sorted(KNOWN_WRITERS)
    if writers != expected:
        added = sorted(set(writers) - set(expected))
        missing = sorted(set(expected) - set(writers))
        parts = []
        if added:
            parts.append(f"new writer(s) not yet classified: {added}")
        if missing:
            parts.append(f"expected writer(s) gone: {missing}")
        return _review("; ".join(parts) or "writer set changed", writers)

    checked: list[str] = []
    with tempfile.TemporaryDirectory(prefix="cvg106-probe-") as tmp:
        scratch_root = Path(tmp)
        for filename in expected:
            for check in FILE_CHECKS[filename]:
                scratch = scratch_root / filename / check.__name__
                scratch.mkdir(parents=True, exist_ok=True)
                try:
                    ok, detail = check(root, scratch)
                except Exception as exc:  # a check that cannot run is REVIEW, never a silent pass
                    return _review(f"{filename}: {check.__name__} could not run ({type(exc).__name__})", checked)
                if not ok:
                    return _review(f"{filename}: {detail}", checked)
                checked.append(f"{filename}: {detail}")

    return _pass(
        "every writer stays inside its classified schema: repository writers land inside "
        "the caller's own repository, the reading store holds only a read point and kept "
        "marks per steward, and per-instance security state (signing secret, session "
        "revocation, TLS CA/leaf) is never project truth",
        checked,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="CVG-106: does the app hold no copy of the project's truth?")
    parser.add_argument("root", nargs="?", default=".", help="repository root to probe (default: cwd)")
    args = parser.parse_args(argv)

    result = evaluate(Path(args.root).resolve())
    for line in result.checked:
        print(f"  - {line}")
    if result.passed:
        print("PROJECT-STATE=PASS")
    else:
        print(f"PROJECT-STATE=REVIEW  ({result.reason})")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
