"""Self-test for the experience.v1 conformance kit.

The kit is only as trustworthy as its own demonstration: it must go GREEN
against a body that keeps the promises (``fixtures/sample-good``) and RED — with
named rule failures — against one that does not (``fixtures/sample-bad``). Both
fixtures are **captured app snapshots with a repository half**, written by
``make_fixtures.py`` beside the kit, so a fixture is judged through exactly the
code path a live app is.

The load-bearing test is ``test_every_rule_has_a_negative_fixture``: a rule
nobody can make fail is a rule that proves nothing. The SKIP set is pinned to
Core 10 and Core 11 — the two clauses about how a review is *conducted* — so a
rule cannot quietly drift into SKIP to dodge a failure.

Runnable two ways (the assertions are identical):
  * with pytest:  uv run --with pytest pytest conformance/experience/tests/ -q
  * no deps:      python3 conformance/experience/tests/test_conformance.py

The kit declares no dependencies, so the plain interpreter is enough.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent          # conformance/experience/
RUN = KIT / "run.py"
REPO = KIT.parent.parent                              # the repository root
CONTRACT = REPO / "contracts" / "experience.v1.md"
README = KIT / "README.md"
GOOD = KIT / "fixtures" / "sample-good"
BAD = KIT / "fixtures" / "sample-bad"

#: Rows this kit declares un-judgeable. Core 10 and Core 11 are promises about
#: how a review is CONDUCTED — "is the behavior satisfied?" rather than "does it
#: look the same?", and whether a shape quietly removed a state. Neither leaves
#: an artifact. Pinned here so a rule cannot be moved into SKIP to dodge a
#: failure without this test going red.
EXPECTED_SKIPS = {"10", "11"}


def run_kit(target):
    proc = subprocess.run(
        [sys.executable, str(RUN), str(target), "--json-only"],
        capture_output=True, text=True, timeout=300, check=False,
    )
    assert proc.stdout.strip(), f"kit produced no JSON report; stderr:\n{proc.stderr}"
    return proc.returncode, json.loads(proc.stdout)


def kit_module():
    """The kit itself, loaded from its own path under a unique module name.

    `import run` would collide: every experience kit ships `run.py`, and the
    first one imported wins `sys.modules["run"]` for the whole pytest session.
    """
    import importlib.util
    sys.path.insert(0, str(KIT.parent))          # for `appsnapshot` / `kitreport`
    name = f"kit_{KIT.name.replace('-', '_')}"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, RUN)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def by_rule(report):
    return {r["rule"]: r for r in report["results"]}


def readme_rule_ids():
    """The first column of the README's rule table — what `ledger/checks/verify.py`
    resolves a ledger row's `run.py (rule N)` reference against."""
    return set(re.findall(r"(?m)^\|\s*([\w.]+)\s*\|", README.read_text(encoding="utf-8")))


def core_clause_numbers():
    body = CONTRACT.read_text(encoding="utf-8").split("## Core (the teeth)")[1].split("\n## ")[0]
    return [int(n) for n in re.findall(r"(?m)^(\d+)\.\s", body)]


# --------------------------------------------------------------------------- #
# the two fixtures                                                             #
# --------------------------------------------------------------------------- #
def test_sample_good_passes():
    code, report = run_kit(GOOD)
    failed = [r for r in report["results"] if r["status"] == "FAIL"]
    assert not failed, "sample-good should keep every promise: " + json.dumps(failed, indent=2)
    assert report["verdict"] == "PASS"
    assert code == 0


def test_sample_bad_fails():
    code, report = run_kit(BAD)
    assert report["verdict"] == "FAIL"
    assert code == 1


def test_every_rule_has_a_negative_fixture():
    """Every rule the kit emits either FAILs on sample-bad or is a declared SKIP."""
    _, bad = run_kit(BAD)
    unprovable = [rid for rid, r in by_rule(bad).items()
                  if r["status"] != "FAIL" and rid not in EXPECTED_SKIPS]
    assert not unprovable, f"rules nobody can make fail: {unprovable}"


def test_every_skip_says_why():
    for fixture in (GOOD, BAD):
        _, report = run_kit(fixture)
        for r in report["results"]:
            if r["status"] == "SKIP":
                assert r.get("reason"), f"{r['rule']} SKIPs with no reason"


def test_skip_set_is_pinned():
    _, good = run_kit(GOOD)
    _, bad = run_kit(BAD)
    seen = {r["rule"] for rep in (good, bad) for r in rep["results"] if r["status"] == "SKIP"}
    assert seen <= EXPECTED_SKIPS, f"a rule drifted into SKIP: {sorted(seen - EXPECTED_SKIPS)}"


def test_a_skip_names_what_a_machine_cannot_settle():
    """A SKIP is never a soft pass. Each one says what would have to exist."""
    _, report = run_kit(GOOD)
    for r in report["results"]:
        if r["status"] != "SKIP":
            continue
        reason = r["reason"].lower()
        assert len(reason) > 80, f"{r['rule']} SKIPs with a reason too short to be one"
        assert any(w in reason for w in ("person", "two bodies", "artifact", "record")), \
            f"{r['rule']} does not name what a machine cannot settle: {reason}"


def test_no_skip_still_claims_the_app_is_unbuilt():
    """The companion app ships in `app/`. A reason that says otherwise is stale."""
    for fixture in (GOOD, BAD):
        _, report = run_kit(fixture)
        for r in report["results"]:
            reason = (r.get("reason") or "").lower()
            assert "not built" not in reason and "unbuilt" not in reason, \
                f"{r['rule']} claims the app is unbuilt: {reason}"


# --------------------------------------------------------------------------- #
# the kit against its contract                                                 #
# --------------------------------------------------------------------------- #
def test_every_core_clause_has_a_row():
    """A clause with no row is invisible — nothing looks wrong when it is missing."""
    _, report = run_kit(GOOD)
    judged = {r["clause"] for r in report["results"]}
    missing = [n for n in core_clause_numbers() if n not in judged]
    assert not missing, f"Core clauses with no rule row: {missing}"


def test_rule_ids_match_the_readme_table():
    """`ledger/checks/verify.py` resolves a ledger row's `(rule N)` against this
    table, and a ref pointing confidently at the wrong rule is worse than one
    that dangles."""
    _, report = run_kit(GOOD)
    emitted = {r["rule"] for r in report["results"]}
    listed = readme_rule_ids()
    assert emitted <= listed, f"rules the README never lists: {sorted(emitted - listed)}"


def test_the_report_shape_is_the_shared_one():
    _, report = run_kit(GOOD)
    for key in ("kit", "contract", "target", "results", "summary", "verdict"):
        assert key in report, f"the report is missing {key}"
    assert set(r["status"] for r in report["results"]) <= {"PASS", "FAIL", "SKIP"}


# --------------------------------------------------------------------------- #
# the two-target model                                                         #
# --------------------------------------------------------------------------- #
REPO_READING_RULES = {"5b", "7", "9", "12", "13", "15"}


def test_a_missing_repository_half_skips_rather_than_guesses():
    """A snapshot with no `repo/` must not be judged against whatever checkout
    the kit happens to sit in. Every repository-reading rule SKIPs, naming the
    missing half — a guess here would report another repository's contracts as
    this target's."""
    with tempfile.TemporaryDirectory() as tmp:
        half = Path(tmp) / "app-only"
        half.mkdir()
        for f in GOOD.iterdir():
            if f.is_file():
                shutil.copy2(f, half / f.name)
        _, report = run_kit(half)
        rows = by_rule(report)
        for rid in REPO_READING_RULES:
            assert rows[rid]["status"] == "SKIP", \
                f"{rid} judged a repository the target never carried: {rows[rid]['detail']}"
            assert "repo/" in rows[rid]["reason"], \
                f"{rid} does not name the missing half: {rows[rid]['reason']}"


def test_the_repository_read_is_named_in_the_report():
    """Which repository was read is a fact a reader needs, not an assumption."""
    _, report = run_kit(GOOD)
    assert report.get("repository_kind") == "snapshot"
    assert report.get("repository", "").endswith("repo")


# --------------------------------------------------------------------------- #
# the lessons this kit paid for                                                #
# --------------------------------------------------------------------------- #
def test_a_sort_comparators_own_parentheses_do_not_hide_the_sort():
    """Measured against the live app: home.js sorts with
    `.sort((a, b) => b.needs - a.needs || …)`. A `\\.sort\\([^)]*needs` probe stops
    at the comparator's OWN closing parenthesis — it never reaches `needs` — and
    reported a correctly-sorted body as unsorted. A fabricated finding."""
    home = "const s = [...list].sort((a, b) => b.needs - a.needs || 0);"
    hits = [m for m in re.finditer(r"\.sort\(", home)]
    assert any("needs" in home[m.end():m.end() + 160] for m in hits)
    assert not re.search(r"\.sort\([^)]*needs", home), \
        "the narrow probe would have matched, so this test proves nothing"


def test_a_keyword_is_not_a_citation():
    """Rule 12 once linked a route to a clause by searching for the route's own
    word, and every link it produced was fabricated: `keep` matched "keeps a
    teammate on plain tooling a first-class participant", `read` matched
    "something a person can read". The kit now carries hand-written citations
    and re-reads each one."""
    kit = kit_module()
    prose = ("Two stewards both running Converge still meet as Converge · host · "
             "Converge, and that keeps a teammate on plain tooling a first-class "
             "participant, and keeps the seam something a person can read.")
    for token in ("keep", "read"):
        assert re.search(rf"\b{token}", prose, re.I), "the bad match is the premise"
    assert all(not p.search("/api/managers/{mid}/publish")
               for p, _, _, _ in kit.CONTRACT_NAMED_WRITES), \
        "a write no contract names must have no citation"


def test_every_citation_still_reads_true_in_this_repository():
    """A citation nobody re-reads is a citation that rots. Each entry in the
    table must still be findable in the clause it names, in THIS repository."""
    kit = kit_module()
    import repotarget
    repo = repotarget.Repo(REPO, "checkout")
    for _pattern, contract, clause, phrase in kit.CONTRACT_NAMED_WRITES:
        where = kit.verify_citation(repo, contract, clause, phrase)
        assert where, (f"stale citation: {contract} "
                       f"{'Core %s' % clause if clause else 'Reserved'} no longer says "
                       f"{phrase.pattern!r}")


def test_a_details_fold_is_where_a_machine_word_belongs():
    """Core 6 does not ask for silence. A machine word inside a Details fold is
    the clause being KEPT, and reading it as a violation would report the app's
    own good behaviour as a defect."""
    kit = kit_module()
    folded = "<p>Working</p><details><summary>Details</summary><p>RESOLVED</p></details>"
    assert not kit.MACHINE_STATE_RE.search(kit.strip_details_folds(folded))
    exposed = "<p>RESOLVED</p>"
    assert kit.MACHINE_STATE_RE.search(kit.strip_details_folds(exposed))


def test_the_plain_word_and_the_machine_word_differ_only_by_case():
    """`Done` is the plain word and `DONE` is the machine's. The match is
    case-sensitive on purpose: making it insensitive erases the whole clause."""
    kit = kit_module()
    assert kit.MACHINE_STATE_RE.search("phase: DONE")
    assert not kit.MACHINE_STATE_RE.search("phase: Done")


def test_a_payload_is_not_a_surface():
    """Rule 6b reads what the app WRITES DOWN; a word rendered out of a payload
    is rule 6a's to judge. Reading payloads here would report every row twice
    and name the wrong fix."""
    _, report = run_kit(BAD)
    exposed = by_rule(report)["6b"].get("exposed") or {}
    assert not [r for r in exposed if r.startswith("/api/")], \
        f"6b judged an API payload: {sorted(exposed)}"


def voice_snapshot(index_html: str):
    """The smallest thing `says_so` and rule 14 read: a shell and no scripts."""
    class Stub:
        def text(self, route):
            return index_html if route == "/" else ""

        def script_text(self):
            return ""
    return Stub()


def test_a_sentence_saying_a_form_is_absent_is_not_an_offer_of_it():
    """Measured on this tree, 2026-09-04 (converge-gl6). Rule 14's third
    feedback form was detected with `\\bvoice\\b`, so the moment the app added
    its own Core 14 sentence — "A voice note is not recorded here" — the word
    appeared in what the app serves and the rule stopped counting voice absent:
    `cannot_do` went from `[priority, feedback as voice]` to `[priority]`. The
    body was rewarded for SAYING it cannot do a thing by no longer being asked
    about it, and nothing was left that would notice voice going missing.

    Every marker is now offer-shaped — a control, a MIME filter, a recorder
    API — so prose about the absence reads as prose."""
    kit = kit_module()
    voice = dict(kit.FEEDBACK_FORMS)["voice"]
    prose = ("Feedback as a voice note &mdash; not here. A voice note is not "
             "recorded here, say it in the Manager Console, or drop the audio "
             "file into the project's .converge/feedback/ folder.")
    assert not voice.search(prose), \
        "prose about the absence of voice still reads as an offer of voice"
    assert not voice.search("<!-- voice -->"), "a comment satisfies the detector"
    for offer in ('<input type="file" accept="audio/*" />',
                  "new MediaRecorder(stream)",
                  '<input id="feedbackVoice" type="file" />'):
        assert voice.search(offer), f"a real offer went undetected: {offer}"


def test_a_heading_that_says_not_here_is_only_half_the_clause():
    """Core 14 asks for two things — "what the limit is, and what to do
    instead" — and the rule read only the first, loosely. Measured on this
    tree, 2026-09-04 (converge-gl6): deleting the whole limit sentence from
    `app/templates/shell.html` left just the heading "Raise or lower a priority
    &mdash; not here", and rule 14 still PASSed on it. `<strong>` and the
    `<span>` beneath it are two statements, and half of one is not the clause.
    """
    kit = kit_module()
    heading_only = ('<p><strong>Raise or lower a priority &mdash; not here'
                    '</strong></p>')
    assert kit.says_so(voice_snapshot(heading_only), "priority") == "", \
        "a heading with the thing and the negation in different statements passed"

    limit_only = (heading_only + '<span>This app has no control that raises or '
                  'lowers a priority, and answers no route that would write one.'
                  '</span>')
    assert kit.says_so(voice_snapshot(limit_only), "priority") == "limit", \
        "the limit alone was read as the whole clause"

    both = (limit_only + '<span>The manager session can: say "Put the priority '
            'write at the top of the queue." Filed as converge-a5g.</span>')
    assert kit.says_so(voice_snapshot(both), "priority") == "both", \
        "the app's own two-part statement is not recognised as complete"


def test_the_measured_regression_runs_through_the_whole_kit():
    """The two halves above, end to end on a real snapshot rather than a stub.

    Take the good fixture, withdraw its voice control, and say so in prose the
    way the app does. Voice must come back into `cannot_do` — the offer is
    gone — and the verdict must turn on whether the prose names somewhere else
    to do it."""
    kit_14 = lambda report: by_rule(report)["14"]  # noqa: E731

    def snapshot_saying(sentence):
        tmp = tempfile.mkdtemp()
        target = Path(tmp) / "voice-withdrawn"
        shutil.copytree(GOOD, target)
        index = target / "index.html"
        html = index.read_text(encoding="utf-8")
        html = re.sub(r'<div class="dialog-field"><label for="feedbackVoice".*?</div>',
                      f"<p>{sentence}</p>", html, flags=re.S)
        assert 'accept="audio' not in html, "the offer survived the withdrawal"
        index.write_text(html, encoding="utf-8")
        return target

    silent = snapshot_saying("Feedback is taken here as text and as a screenshot.")
    row = kit_14(run_kit(silent)[1])
    assert row["status"] == "FAIL" and "feedback as voice" in row["cannot_do"], \
        f"withdrawing the control left voice unnoticed: {row}"
    assert "feedback as voice" in row["said_nothing_about"], row

    half = snapshot_saying("A voice note is not recorded here.")
    row = kit_14(run_kit(half)[1])
    assert row["status"] == "FAIL", \
        f"saying only that voice is absent passed the whole clause: {row}"
    assert "feedback as voice" in row["cannot_do"], \
        "the sentence about the absence was read as an offer"
    assert "feedback as voice" in row["limit_stated_no_redirect"], row

    whole = snapshot_saying(
        "A voice note is not recorded here &mdash; say it in the Manager "
        "Console, or drop the audio file into the project's feedback folder.")
    row = kit_14(run_kit(whole)[1])
    assert row["status"] == "PASS", f"both halves said, and the rule still failed: {row}"
    assert "feedback as voice" in row["cannot_do"], \
        "a body that states its limit is excused from having one"


def test_an_exempt_route_is_exempt_because_a_contract_says_what_it_is():
    """A route is exempt from the five-writes count because a contract names it,
    never because counting it would be inconvenient."""
    kit = kit_module()
    for route in ("/login", "/logout", "/api/tmux/hw/session/keys"):
        why = kit.exempt_write(route)
        assert why and ("app/auth.py" in why or "experience-console.v1" in why), \
            f"{route} is exempt with no contract behind it: {why}"
    assert kit.exempt_write("/api/managers/{mid}/publish") is None


def test_a_per_person_store_that_is_not_your_reading_is_still_a_second_copy():
    """Clause 7, ratified 2026-09-06, widened what a body may keep by ONE named
    thing — your own reading, kept per person outside the repository — not by
    "anything kept outside the repository". A per-person store of the project's
    work queue is still a second copy of the truth, and rule 7 must still refuse
    it. Without this the ratification would have turned the rule into a rule
    about WHERE a store lives rather than WHAT it holds.
    """
    kit = kit_module()
    import repotarget
    ratified = CONTRACT.read_text(encoding="utf-8")
    assert kit.CLAUSE7_ALLOWS_THE_READING.search(ratified), \
        "the premise: this repository's clause 7 is the ratified one"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "contracts").mkdir()
        (root / "app").mkdir()
        (root / "contracts" / "experience.v1.md").write_text(ratified, encoding="utf-8")
        repo = repotarget.Repo(root, "checkout")

        queue_cache = root / "app" / "queue_cache.py"
        queue_cache.write_text(
            '"""A copy of the project\'s work queue, one file per person."""\n'
            "from pathlib import Path\n"
            'PATH = Path.home() / ".amplifier" / "work-items.json"\n',
            encoding="utf-8")
        refused = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert refused["status"] == "FAIL", refused
        assert "queue_cache.py" in refused["detail"], refused

        queue_cache.unlink()
        (root / "app" / "state_store.py").write_text(
            '"""Where each steward\'s own reading is remembered, per person: the\n'
            'read point, and the kept marks."""\n'
            "from pathlib import Path\n"
            'PATH = Path.home() / ".amplifier" / "converge-app.state.json"\n',
            encoding="utf-8")
        allowed = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert allowed["status"] == "PASS", allowed


def test_auth_revocation_state_is_not_a_copy_of_the_projects_truth():
    """converge-lech, repaired.

    `app/auth.py`'s `SessionRegistry` persists `{"revoked": [...]}` -- which
    session ids a logout has ended -- in a JSON file under `Path.home()`. That
    matches STORE_MARKERS ("a JSON file of its own"), but clause 7 names six
    things as the project's truth (documents, code record, work queue, lanes,
    return log, pending decisions) and "who is still signed in" is none of
    them. Rule 7 must not report the app's own good security practice as a
    defect, and must not need the filename `auth.py` to say so -- the same
    content, in a differently-named file, must be read the same way.

    A word-only fixture (`is_revoked` reading a bare `table.get('revoked')`,
    `revoke` doing nothing) is no longer a positive control here: the rule no
    longer grants the exemption for revocation-sounding words, only for the
    bounded persisted schema itself. So this copies the real shape --
    initialized to exactly `{"revoked": []}`, read via `.get`/`.setdefault`,
    written via a `["revoked"] = ...` assignment, handed to `json.dump` --
    under a different class and file name, proving the recognizer reads
    content, not identifiers.
    """
    kit = kit_module()
    import repotarget
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "contracts").mkdir()
        (root / "app").mkdir()
        (root / "contracts" / "experience.v1.md").write_text(ratified, encoding="utf-8")
        repo = repotarget.Repo(root, "checkout")

        # Not named auth.py, and not called SessionRegistry, on purpose: the
        # classifier reads content, not a filename or class-name allowlist.
        revocation_store = root / "app" / "session_state.py"
        revocation_store.write_text(
            '"""Which issued session ids a logout has ended."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "class LogoutLedger:\n"
            "    def _read(self):\n"
            "        if not self.path.exists():\n"
            '            return {"revoked": []}\n'
            "        table = json.loads(self.path.read_text())\n"
            '        table.setdefault("revoked", [])\n'
            "        return table\n\n"
            "    def is_revoked(self, sid):\n"
            "        return sid in self._read().get('revoked', [])\n\n"
            "    def revoke(self, sid):\n"
            "        table = self._read()\n"
            '        revoked = set(table.get("revoked") or [])\n'
            "        revoked.add(sid)\n"
            '        table["revoked"] = sorted(revoked)\n'
            "        with open(self.path, 'w') as out:\n"
            "            json.dump(table, out)\n\n"
            'PATH = Path.home() / ".amplifier" / "app.sessions.json"\n',
            encoding="utf-8")
        allowed = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert allowed["status"] == "PASS", allowed


def test_a_project_cache_disguised_with_revocation_words_still_fails():
    """converge-lech's own negative control: `carries_project_truth` outranks
    `is_auth_state`. A store that mentions revocation vocabulary AND actually
    persists the project's work queue is still a second copy of the truth --
    named regardless of the file it sits in, and regardless of being kept
    per person (the same principle `test_a_per_person_store_that_is_not_your_\
reading_is_still_a_second_copy` already established for the reading
    exemption).
    """
    kit = kit_module()
    import repotarget
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "contracts").mkdir()
        (root / "app").mkdir()
        (root / "contracts" / "experience.v1.md").write_text(ratified, encoding="utf-8")
        repo = repotarget.Repo(root, "checkout")

        disguised = root / "app" / "auth.py"
        disguised.write_text(
            '"""SessionRegistry: is_revoked, revoked, revoke -- and, quietly,\n'
            "a per-person copy of the project's work queue too.\"\"\"\n"
            "from pathlib import Path\n"
            'PATH = Path.home() / ".amplifier" / "auth.json"\n',
            encoding="utf-8")
        refused = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert refused["status"] == "FAIL", refused
        assert "auth.py" in refused["detail"], refused


def _repo_with_app_file(root, ratified, filename, content):
    """A minimal repository checkout carrying one file under `app/`.

    Shared by the serialized-shape tests below so each one states only what
    differs: the store's own content.
    """
    import repotarget
    (root / "contracts").mkdir()
    (root / "app").mkdir()
    (root / "contracts" / "experience.v1.md").write_text(ratified, encoding="utf-8")
    (root / "app" / filename).write_text(content, encoding="utf-8")
    return repotarget.Repo(root, "checkout")


def test_a_serialized_lane_cache_with_no_prose_is_still_project_truth():
    """converge-lech, reopened -- the exact reproduction.

    `cache = {"lanes": [{"id": "lane-1", "state": "working"}]}` beside a bare
    `def revoke(sid): ...`, with NO prose anywhere in the file. Before this
    fix: `PROJECT_TRUTH_MARKERS` reads prose only, finds nothing (the word
    "lane" appears nowhere as a phrase), `AUTH_STATE_MARKERS` finds `revoke`,
    and the store was granted the auth exemption though it serializes exactly
    the lane records clause 7 names -- a false PASS. This must FAIL.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "lane_cache.py",
            '"""Serialized lane cache, no explanatory prose."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            'cache = {"lanes": [{"id": "lane-1", "state": "working"}]}\n\n'
            "def revoke(sid):\n"
            "    pass\n\n"
            'PATH = Path.home() / ".amplifier" / "lane_cache.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "lane_cache.py" in result["detail"], result


def test_serialized_project_shapes_are_recognized_without_prose():
    """The other explicit project categories, each with no prose: a document
    store, a work-queue store, a pending-decisions store, and a return-log
    store. Every one must FAIL -- the content is the project's truth whether
    or not any file says so in a sentence."""
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    cases = {
        "doc_cache.py": 'snapshot = {"documents": [{"path": "docs/VISION.md"}]}\n',
        "queue_cache.py": 'snapshot = {"work_items": [{"id": "converge-1"}]}\n',
        "decision_cache.py": 'snapshot = {"decisions": [{"id": "d-1"}]}\n',
        "log_cache.py": 'snapshot = {"return_log": [{"lane": "x"}]}\n',
    }
    for filename, body in cases.items():
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo_with_app_file(
                Path(tmp), ratified, filename,
                '"""No explanatory prose here -- data only."""\n'
                "from pathlib import Path\n"
                + body +
                f'PATH = Path.home() / ".amplifier" / "{filename}.json"\n')
            result = kit.check_no_copy_of_the_projects_truth(None, repo)
            assert result["status"] == "FAIL", f"{filename}: {result}"
            assert filename in result["detail"], f"{filename}: {result}"


def test_a_mixed_auth_plus_project_payload_still_fails():
    """A single store that genuinely holds BOTH revocation state and a
    serialized project shape -- `{"revoked": [...], "lanes": [...]}` -- is
    still a second copy of the truth. Revocation vocabulary sitting beside
    real project data must never launder it into the auth exemption."""
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "mixed_store.py",
            '"""Session table, plus (quietly) a lane cache."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "def revoke(sid):\n"
            "    table = json.loads(PATH.read_text())\n"
            '    table.setdefault("revoked", []).append(sid)\n'
            '    table["lanes"] = [{"id": "lane-1", "state": "working"}]\n'
            "    PATH.write_text(json.dumps(table))\n\n"
            'PATH = Path.home() / ".amplifier" / "mixed_store.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "mixed_store.py" in result["detail"], result


def test_a_per_person_serialized_cache_is_still_project_truth():
    """A per-person cache (kept per `Path.home()`, the very shape clause 7's
    reading exemption uses) that ALSO serializes project data is still a
    second copy of the truth -- being per-person is not what clause 7 asks
    about, what the store holds is."""
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "per_person_cache.py",
            '"""Per-person, on purpose -- still a copy of the queue."""\n'
            "from pathlib import Path\n\n"
            'cache = {"queue": [{"id": "converge-1", "state": "open"}]}\n\n'
            'PATH = Path.home() / ".amplifier" / "per-person-cache.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "per_person_cache.py" in result["detail"], result


def test_a_real_revocation_only_store_still_passes_alongside_the_new_markers():
    """Regression control: the new serialized-shape markers must not start
    faulting the store clause 7 already allows. A store that matches the
    bounded SessionRegistry schema -- and nothing beyond it -- is still the
    permitted per-instance authentication state.

    A word-only `revoke`/`is_revoked` fixture with no actual persistence
    (`revoke` doing nothing) is no longer a positive control: see
    `test_a_variable_or_scalar_lane_payload_beside_bare_revoke_still_fails`
    for exactly why that shape must not pass any more. This copies the real
    persisted schema instead.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "sessions.py",
            '"""Which issued session ids a logout has ended."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "class SessionRegistry:\n"
            "    def _read(self):\n"
            "        if not self.path.exists():\n"
            '            return {"revoked": []}\n'
            "        table = json.loads(self.path.read_text())\n"
            '        table.setdefault("revoked", [])\n'
            "        return table\n\n"
            "    def is_revoked(self, sid):\n"
            "        return sid in self._read().get('revoked', [])\n\n"
            "    def revoke(self, sid):\n"
            "        table = self._read()\n"
            '        revoked = set(table.get("revoked") or [])\n'
            "        revoked.add(sid)\n"
            '        table["revoked"] = sorted(revoked)\n'
            "        with open(self.path, 'w') as out:\n"
            "            json.dump(table, out)\n\n"
            'PATH = Path.home() / ".amplifier" / "sessions.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "PASS", result


def test_a_variable_or_scalar_lane_payload_beside_bare_revoke_still_fails():
    """converge-lech, repaired -- the escape the previous two blacklist
    refinements still permitted.

    `SERIALIZED_PROJECT_TRUTH_MARKERS` only matches a literal list value
    (`"lanes": [`). A lane payload assigned from a variable, or a bare
    scalar, matches no project-truth marker -- and the old blacklist's bare
    `revoke` word still matched, granting the auth exemption though the
    store is neither the reading nor session-revocation state. The positive
    recognizer only exempts a store that matches the bounded SessionRegistry
    schema byte for byte; neither of these does, so both must FAIL.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    cases = {
        "variable_lane_cache.py": (
            'records = [{"id": "lane-1", "state": "working"}]\n'
            'cache = {"lanes": records}\n\n'
            "def revoke(sid):\n"
            "    pass\n"),
        "scalar_lane_cache.py": (
            'cache = {"lanes": "lane-1"}\n\n'
            "def revoke(sid):\n"
            "    pass\n"),
    }
    for filename, body in cases.items():
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo_with_app_file(
                Path(tmp), ratified, filename,
                '"""No explanatory prose here -- data only."""\n'
                "from pathlib import Path\n"
                + body +
                f'PATH = Path.home() / ".amplifier" / "{filename}.json"\n')
            result = kit.check_no_copy_of_the_projects_truth(None, repo)
            assert result["status"] == "FAIL", f"{filename}: {result}"
            assert filename in result["detail"], f"{filename}: {result}"


def test_an_unrelated_json_store_that_merely_says_revoke_still_fails():
    """A JSON store with no relation to session revocation at all -- an
    ordinary cache key, no `{"revoked": [...]}` schema anywhere -- but the
    word `revoke` happens to appear in an unrelated function name. The
    positive recognizer requires the bounded schema, not the word; this
    must FAIL.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "unrelated_cache.py",
            '"""An unrelated cache; happens to mention revoke."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "def revoke_stale_entries(cache):\n"
            '    cache.pop("stale", None)\n\n'
            'state = {"last_seen": "2026-09-09"}\n\n'
            'PATH = Path.home() / ".amplifier" / "unrelated_cache.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "unrelated_cache.py" in result["detail"], result


def test_a_table_touching_revoked_and_another_key_still_fails():
    """converge-lech, repaired: the bounded schema requires the persisted
    table touch NO literal key beyond "revoked". A table that also reads or
    writes one other literal key -- even one none of clause 7's six
    project-truth categories names, so `carries_project_truth` never fires
    -- is not the permitted SessionRegistry shape and must FAIL, not be
    waved through on a bare `revoke` word.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "extra_key_store.py",
            '"""Session table that also keeps an unrelated counter."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "def revoke(sid):\n"
            "    table = json.loads(PATH.read_text()) if PATH.exists() "
            'else {"revoked": []}\n'
            '    revoked = set(table.get("revoked") or [])\n'
            "    revoked.add(sid)\n"
            '    table["revoked"] = sorted(revoked)\n'
            '    table["hits"] = table.get("hits", 0) + 1\n'
            "    with open(PATH, 'w') as out:\n"
            "        json.dump(table, out)\n\n"
            'PATH = Path.home() / ".amplifier" / "extra_key_store.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "extra_key_store.py" in result["detail"], result


def test_a_separately_persisted_unknown_cache_beside_the_valid_table_still_fails():
    """converge-lech, reopened a second time.

    `recognizes_session_registry_schema` used to ask `any(...)` across every
    `json.dump` call site: a file with a REAL, valid revoked-only
    SessionRegistry table (`json.dump(table, out)`, touching only
    `"revoked"`) ALSO separately persisting an unrelated cache
    (`json.dump(cache, out)`, `cache = {"lanes": records}` -- a variable
    value, so `SERIALIZED_PROJECT_TRUTH_MARKERS`' literal-list pattern never
    fires either) still PASSed, because the one matching `table` alone
    satisfied `any()`. Every `json.dump` write target in the file must now be
    accounted for and satisfy the bounded schema; this second, unaccounted
    target must fail the whole file.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "dual_store.py",
            '"""A real SessionRegistry table, plus an unrelated, separately\n'
            'persisted lane cache the old any()-based recognizer never\n'
            'weighed against the rest of the file."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "class SessionRegistry:\n"
            "    def _read(self):\n"
            "        if not self.path.exists():\n"
            '            return {"revoked": []}\n'
            "        table = json.loads(self.path.read_text())\n"
            '        table.setdefault("revoked", [])\n'
            "        return table\n\n"
            "    def revoke(self, sid):\n"
            "        table = self._read()\n"
            '        revoked = set(table.get("revoked") or [])\n'
            "        revoked.add(sid)\n"
            '        table["revoked"] = sorted(revoked)\n'
            "        with open(self.path, 'w') as out:\n"
            "            json.dump(table, out)\n\n"
            "def snapshot_lanes(records):\n"
            '    cache = {"lanes": records}\n'
            "    with open(CACHE_PATH, 'w') as out:\n"
            "        json.dump(cache, out)\n\n"
            'PATH = Path.home() / ".amplifier" / "dual_store.sessions.json"\n'
            'CACHE_PATH = Path.home() / ".amplifier" / "dual_store.lanes.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "dual_store.py" in result["detail"], result


def test_an_unknown_expression_dumped_alongside_the_valid_table_still_fails():
    """converge-lech, reopened a second time.

    The old `\\bjson\\.dump\\(\\s*(\\w+)\\s*,` regex silently skipped any
    `json.dump` call whose first argument was not a bare identifier -- a
    nonidentifier expression (here, a function call) was never enumerated as
    a target at all, so it was never checked and never counted against the
    file. A file with a real, valid revoked-only table (`json.dump(table,
    out)`) ALSO dumping an unrelated expression this recognizer cannot vouch
    for (`json.dump(collect_debug_snapshot(), out)`) must fail the whole
    file -- an unaccounted target is not the same as an absent one.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "expr_dump_store.py",
            '"""A real SessionRegistry table, plus an unrelated dump of a\n'
            'nonidentifier expression the recognizer must not silently\n'
            'ignore."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "class SessionRegistry:\n"
            "    def _read(self):\n"
            "        if not self.path.exists():\n"
            '            return {"revoked": []}\n'
            "        table = json.loads(self.path.read_text())\n"
            '        table.setdefault("revoked", [])\n'
            "        return table\n\n"
            "    def revoke(self, sid):\n"
            "        table = self._read()\n"
            '        revoked = set(table.get("revoked") or [])\n'
            "        revoked.add(sid)\n"
            '        table["revoked"] = sorted(revoked)\n'
            "        with open(self.path, 'w') as out:\n"
            "            json.dump(table, out)\n\n"
            "def collect_debug_snapshot():\n"
            '    return {"last_seen": "2026-09-09"}\n\n'
            "def dump_debug_snapshot():\n"
            "    with open(DEBUG_PATH, 'w') as out:\n"
            "        json.dump(collect_debug_snapshot(), out)\n\n"
            'PATH = Path.home() / ".amplifier" / "expr_dump_store.sessions.json"\n'
            'DEBUG_PATH = Path.home() / ".amplifier" / "expr_dump_store.debug.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "expr_dump_store.py" in result["detail"], result


def test_a_keyword_only_dump_target_beside_the_valid_table_still_fails():
    """converge-lech, reopened a third time -- the manager's own reproduction.

    `json.dump`'s real signature is `dump(obj, fp, ...)`, both keyword-
    capable. `_json_dump_targets` only ever read `node.args[0]`, and only
    entered its branch when `node.args` was non-empty at all -- so a call
    written keyword-only, `json.dump(obj=cache, fp=out)`, had an EMPTY
    `node.args` and was skipped outright: never enumerated, never counted
    as unknown, invisible. A file with a real, valid revoked-only
    SessionRegistry table (`json.dump(table, out)`) ALSO separately
    persisting an unrelated lane cache this way (`cache = {"lanes":
    records}`, `json.dump(obj=cache, fp=out)`) must fail the whole file --
    the same as the second reopening's positional nonidentifier expression,
    just reached by keyword instead of by position.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "kwonly_dump_store.py",
            '"""A real SessionRegistry table, plus an unrelated lane cache\n'
            'dumped with a keyword-only `obj=`, which the old positional-only\n'
            'enumeration never even looked at."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "class SessionRegistry:\n"
            "    def _read(self):\n"
            "        if not self.path.exists():\n"
            '            return {"revoked": []}\n'
            "        table = json.loads(self.path.read_text())\n"
            '        table.setdefault("revoked", [])\n'
            "        return table\n\n"
            "    def revoke(self, sid):\n"
            "        table = self._read()\n"
            '        revoked = set(table.get("revoked") or [])\n'
            "        revoked.add(sid)\n"
            '        table["revoked"] = sorted(revoked)\n'
            "        with open(self.path, 'w') as out:\n"
            "            json.dump(table, out)\n\n"
            "def snapshot_lanes(records):\n"
            '    cache = {"lanes": records}\n'
            "    with open(CACHE_PATH, 'w') as out:\n"
            "        json.dump(obj=cache, fp=out)\n\n"
            'PATH = Path.home() / ".amplifier" / "kwonly_dump_store.sessions.json"\n'
            'CACHE_PATH = Path.home() / ".amplifier" / "kwonly_dump_store.lanes.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "kwonly_dump_store.py" in result["detail"], result


def test_a_keyword_only_dump_of_the_valid_table_itself_still_passes():
    """Positive control paired with the test above: `obj=`/`fp=` keyword
    syntax is not itself disqualifying -- only an unaccounted SECOND target
    is. The real table, dumped entirely by keyword and touching no key
    beyond "revoked", must still PASS.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "kwonly_valid_store.py",
            '"""The real SessionRegistry schema, dumped entirely by keyword."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "class SessionRegistry:\n"
            "    def _read(self):\n"
            "        if not self.path.exists():\n"
            '            return {"revoked": []}\n'
            "        table = json.loads(self.path.read_text())\n"
            '        table.setdefault("revoked", [])\n'
            "        return table\n\n"
            "    def revoke(self, sid):\n"
            "        table = self._read()\n"
            '        revoked = set(table.get("revoked") or [])\n'
            "        revoked.add(sid)\n"
            '        table["revoked"] = sorted(revoked)\n'
            "        with open(self.path, 'w') as out:\n"
            "            json.dump(obj=table, fp=out)\n\n"
            'PATH = Path.home() / ".amplifier" / "kwonly_valid_store.sessions.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "PASS", result


def test_a_json_dump_call_with_no_locatable_target_still_fails():
    """Unknown-argument control. A `json.dump(...)` call offering neither a
    positional argument nor an `obj=` keyword -- e.g. only `fp=`, or no
    arguments recognizable as the object at all -- cannot be located, and
    must be conservatively counted as an unknown target (the same treatment
    a nonidentifier expression already gets), never silently skipped.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "unlocatable_dump_store.py",
            '"""A real SessionRegistry table, plus a json.dump call whose\n'
            'target argument cannot be located by name or position at all."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "class SessionRegistry:\n"
            "    def _read(self):\n"
            "        if not self.path.exists():\n"
            '            return {"revoked": []}\n'
            "        table = json.loads(self.path.read_text())\n"
            '        table.setdefault("revoked", [])\n'
            "        return table\n\n"
            "    def revoke(self, sid):\n"
            "        table = self._read()\n"
            '        revoked = set(table.get("revoked") or [])\n'
            "        revoked.add(sid)\n"
            '        table["revoked"] = sorted(revoked)\n'
            "        with open(self.path, 'w') as out:\n"
            "            json.dump(table, out)\n\n"
            "def dump_mystery(fp=None, **extra):\n"
            "    json.dump(fp=fp, **extra)\n\n"
            'PATH = Path.home() / ".amplifier" / "unlocatable_dump_store.sessions.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "unlocatable_dump_store.py" in result["detail"], result


def test_a_hyphenated_key_on_the_tracked_table_still_fails():
    """converge-lech, reopened a fourth time -- the manager's own
    reproduction. `_table_matches_session_registry_schema` used to read keys
    with a `\\w+`-anchored regex, so `table["extra-cache"] = records` -- a
    real second key, just not an identifier-shaped one, a hyphen is not a
    word character -- matched no key regex at all and was invisible: not
    counted as an extra key, just never seen. A table that also writes one
    other literal key, hyphenated, still fails -- the same as the earlier
    `test_a_table_touching_revoked_and_another_key_still_fails` control, just
    with a key `\\w+` cannot see.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "hyphen_key_store.py",
            '"""Session table that also keeps an unrelated, hyphenated key."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "def revoke(sid):\n"
            "    table = json.loads(PATH.read_text()) if PATH.exists() "
            'else {"revoked": []}\n'
            '    revoked = set(table.get("revoked") or [])\n'
            "    revoked.add(sid)\n"
            '    table["revoked"] = sorted(revoked)\n'
            '    table["extra-cache"] = revoked\n'
            "    with open(PATH, 'w') as out:\n"
            "        json.dump(table, out)\n\n"
            'PATH = Path.home() / ".amplifier" / "hyphen_key_store.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "hyphen_key_store.py" in result["detail"], result


def test_an_empty_string_key_on_the_tracked_table_still_fails():
    """Same blind spot as the hyphenated key, taken to its edge: an empty
    string is a legal dict key that `\\w+` (one or more word characters)
    can never match at all, `\\w*` would be needed and still was not used.
    AST literal-key inspection has no such gap -- any string constant is a
    key, including `""`.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "empty_key_store.py",
            '"""Session table that also keeps an empty-string key."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "def revoke(sid):\n"
            "    table = json.loads(PATH.read_text()) if PATH.exists() "
            'else {"revoked": []}\n'
            '    revoked = set(table.get("revoked") or [])\n'
            "    revoked.add(sid)\n"
            '    table["revoked"] = sorted(revoked)\n'
            '    table[""] = "marker"\n'
            "    with open(PATH, 'w') as out:\n"
            "        json.dump(table, out)\n\n"
            'PATH = Path.home() / ".amplifier" / "empty_key_store.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "empty_key_store.py" in result["detail"], result


def test_a_dynamic_key_access_on_the_tracked_table_still_fails():
    """Unknown-key control. A key reached through a variable or expression
    rather than a string literal -- `table[cache_key] = value` -- cannot be
    proven to be "revoked" or anything else. Unknown/dynamic key access must
    not positively qualify a table as revoked-only; it disqualifies it, the
    same as a second, known, unrelated key does.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "dynamic_key_store.py",
            '"""Session table that also writes through a dynamic key."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "def revoke(sid, cache_key):\n"
            "    table = json.loads(PATH.read_text()) if PATH.exists() "
            'else {"revoked": []}\n'
            '    revoked = set(table.get("revoked") or [])\n'
            "    revoked.add(sid)\n"
            '    table["revoked"] = sorted(revoked)\n'
            "    table[cache_key] = sid\n"
            "    with open(PATH, 'w') as out:\n"
            "        json.dump(table, out)\n\n"
            'PATH = Path.home() / ".amplifier" / "dynamic_key_store.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "dynamic_key_store.py" in result["detail"], result


def test_a_dynamic_get_key_on_the_tracked_table_still_fails():
    """Same unknown-key reasoning, on the read side: `table.get(some_var)`
    reaches an unproven key through `.get`/`.setdefault` rather than a
    literal. It must not be silently ignored (dropped from the key set,
    letting the file read as if `.get` were never called) or wrongly
    counted as reading "revoked" -- either way, an unknown read disqualifies
    the file.
    """
    kit = kit_module()
    ratified = CONTRACT.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo_with_app_file(
            Path(tmp), ratified, "dynamic_get_store.py",
            '"""Session table also read through a dynamic .get key."""\n'
            "from pathlib import Path\n"
            "import json\n\n"
            "def revoke(sid, field):\n"
            "    table = json.loads(PATH.read_text()) if PATH.exists() "
            'else {"revoked": []}\n'
            '    revoked = set(table.get("revoked") or [])\n'
            "    revoked.add(sid)\n"
            '    table["revoked"] = sorted(revoked)\n'
            "    _ = table.get(field)\n"
            "    with open(PATH, 'w') as out:\n"
            "        json.dump(table, out)\n\n"
            'PATH = Path.home() / ".amplifier" / "dynamic_get_store.json"\n')
        result = kit.check_no_copy_of_the_projects_truth(None, repo)
        assert result["status"] == "FAIL", result
        assert "dynamic_get_store.py" in result["detail"], result


def test_rule_7_reads_the_clause_and_not_the_reserved_section():
    """Before the ratification the arbiter was the umbrella's Reserved section,
    which asked where the reading cursor was kept. That question is answered and
    deleted, so a rule still reading it would report the app's own good
    behaviour as a defect.
    """
    kit = kit_module()
    import repotarget
    repo = repotarget.Repo(REPO, "checkout")
    reserved = kit.reserved_section(CONTRACT.read_text(encoding="utf-8"))
    assert not re.search(r"reading cursor", reserved, re.I), \
        "the premise: the Reserved question is gone"
    assert kit.check_no_copy_of_the_projects_truth(None, repo)["status"] == "PASS"
    for _pattern, contract, clause, phrase in kit.CONTRACT_NAMED_WRITES:
        if phrase.pattern.startswith("kept per person"):
            assert clause == 7, "the read route is cited to a clause, not to Reserved"
            break
    else:
        raise AssertionError("no citation for the read route")


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok    {name}")
            except AssertionError as exc:
                failures.append(name)
                print(f"  FAIL  {name}: {exc}")
    print(f"\n{len(failures)} failure(s)")
    raise SystemExit(1 if failures else 0)
