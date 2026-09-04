"""The host half of collaboration: pull requests, their comments, and freshness.

`contracts/experience-collaboration.v1.md` fixes a boundary rather than a
feature. Git is the protocol, the repository host carries the conversation, and
Converge is the lens on it. Half of that seam already held before this module
existed -- every write goes through git, a ratification is an ordinary commit,
and one review renderer lays out every proposal. The other half did not exist
at all: nothing here could reach the host.

This module is that reach, and nothing more:

* **Clause 4 -- the bridge.** A pull request is read with the host's own command
  line (``gh``) and laid out as a proposal. A question the steward asks is
  posted back as a comment on that same pull request, so the teammate never
  leaves the tools they already use and the steward never retypes a judgment
  somewhere else.
* **Clause 5 -- the answer goes home.** The steward's word is written to the
  dated ratification record by ``app/writes.py`` *and* posted to the pull
  request it came from, in the steward's own words.
* **Clause 6 -- freshness is not the steward's job.** ``POST
  /api/collab/webhooks/host`` is the door the host calls when it can. When no call has arrived,
  the app asks on a timer instead, and :func:`freshness` says which of the two
  is carrying the surface right now -- in plain words, never silently.
* **Clause 3 -- three origins, one review.** A pull request is turned into the
  same proposal shape ``app/data.py`` builds from a ``*-candidate.md`` file, so
  the review already in Direction lays it out unchanged. Where it came from is
  a value on the proposal (``source``), never a second layout.

Three things this module deliberately is **not**:

1. **Not a channel between two manager sessions.** No route here addresses a
   second manager session, and none can be built from what is here: every
   destination is a pull request on the shared host. Two stewards both running
   Converge still meet as Converge - host - Converge (clause 2).
2. **Not a second collaboration surface.** Nothing is kept here. A comment is
   relayed to the host and read back from it; there is no store, no tracker and
   no thread of its own (clause 10).
3. **Not a write path of its own.** Recording the steward's word is
   ``app/writes.py``'s job and stays there (clauses 1, 7 and 9). This module
   asks it to write, then tells the host what it wrote.

**What is honest about the webhook today.** The route exists and checks a shared
secret, but every ``/api/`` path in this app is behind the sign-in gate in
``app/serve.py``, which this module does not own. Until ``/api/collab/webhooks/host``
is listed as a public path there, a call from the host answers 401 and polling
is what actually keeps the surface fresh. That is exactly the fallback clause 6
asks to be named rather than assumed, so :func:`freshness` names it and the
partial prints it.

Wiring, one line each:

    app.include_router(collab.router)          # app/serve.py
    {% include "collab.html" %}                # app/templates/shell.html
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from . import config, data, writes

router = APIRouter(prefix="/api/collab", tags=["collab"])

#: How often the browser asks the host for itself when nothing calls us.
POLL_SECONDS = 60

#: A call from the host counts as "the host is telling us" for this long.
#: After that the surface says polling again rather than claiming a webhook it
#: has not heard from since breakfast.
WEBHOOK_FRESH_SECONDS = 15 * 60

#: How many open pull requests one reading brings back. A cap keeps a slow host
#: from holding the page, and the answer says the cap was applied.
PULL_LIMIT = 20

#: Seconds any one host command may take before it is given up on.
HOST_TIMEOUT = 20

#: What posting a question actually runs: `gh pr comment <number> --body <text>`.
#: Written out so the command a comment becomes is readable here rather than
#: assembled out of sight.
COMMENT_ARGV = ("gh", "pr", "comment")

#: The path the host calls when something changed. Named here so the surface,
#: the tests and the setup notes all quote one string.
WEBHOOK_PATH = "/api/collab/webhooks/host"

#: Where the shared secret the host signs its calls with is kept.
SECRET_PATH = Path(
    os.environ.get("CONVERGE_COLLAB_SECRET_FILE")
    or (Path.home() / ".amplifier" / "converge-app.webhook-secret")
)

#: The four words a steward may answer with -- the same four `app/writes.py`
#: records, so the host and the record never disagree about the vocabulary.
DECISION_WORDS = dict(writes.DECISION_WORDS)


# --------------------------------------------------------------------------
# the host's own command line
# --------------------------------------------------------------------------
def host_cli() -> str:
    """The path to the host command line, or an empty string when absent."""
    return shutil.which("gh") or ""


def _run(repo: Path, argv: list[str]) -> tuple[bool, str, str]:
    """Run one host command in `repo`. Never raises; never guesses."""
    tool = host_cli()
    if not tool:
        return False, "", (
            "the host command line `gh` is not installed on this machine, so no "
            "pull request can be read and no comment can be posted"
        )
    try:
        done = subprocess.run(
            [tool, *argv], cwd=str(repo), capture_output=True, text=True,
            timeout=HOST_TIMEOUT, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, "", f"the host did not answer within {HOST_TIMEOUT}s ({exc})"
    if done.returncode != 0:
        return False, done.stdout, (done.stderr or done.stdout or "").strip() or (
            f"the host answered {done.returncode} and said nothing"
        )
    return True, done.stdout, ""


def _json(repo: Path, argv: list[str]) -> tuple[object, str]:
    ok, out, why = _run(repo, argv)
    if not ok:
        return None, why
    try:
        return json.loads(out or "null"), ""
    except json.JSONDecodeError:
        return None, "the host answered something that is not JSON"


# --------------------------------------------------------------------------
# a pull request, read as a proposal
# --------------------------------------------------------------------------
def _sections(body: str) -> dict:
    """`{heading lowercased: text}` for a proposal body written in parts."""
    found: dict[str, str] = {}
    head, lines = "", []
    for line in (body or "").splitlines():
        if line.startswith("#"):
            if head:
                found[head] = "\n".join(lines).strip()
            head, lines = line.lstrip("#").strip().lower(), []
            continue
        if line.startswith("**") and line.rstrip().endswith("**") and len(line) < 90:
            if head:
                found[head] = "\n".join(lines).strip()
            head, lines = line.strip("* ").strip().lower(), []
            continue
        lines.append(line)
    if head:
        found[head] = "\n".join(lines).strip()
    return found


def _bullets(text: str) -> list[str]:
    out = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith(("-", "*", "+")):
            said = stripped[1:].strip()
            if said:
                out.append(said)
    return out


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in (text or "").split("\n\n") if p.strip()]


def _key_for(sections: dict, *needles: str) -> str:
    for key in sections:
        if any(needle in key for needle in needles):
            return key
    return ""


def proposal_from_pull(pull: dict, repo_ident: str) -> dict:
    """One pull request in the shape the review already lays out.

    The keys are `app/data.py`'s `proposals_for` keys, so nothing downstream has
    to know a proposal came from the host rather than from a `*-candidate.md`
    file beside a document. `source` and `origin` carry that fact as a value.
    """
    body = str(pull.get("body") or "")
    sections = _sections(body)
    change_key = _key_for(sections, "exact change", "what changes", "the change")
    evidence_key = _key_for(sections, "evidence")
    unchanged_key = _key_for(sections, "not change")
    why_key = _key_for(sections, "why")
    author = ((pull.get("author") or {}) or {}).get("login") or "a teammate"
    number = pull.get("number")

    changes = _bullets(sections.get(change_key, "")) if change_key else []
    if not changes:
        changes = _paragraphs(sections.get(change_key, "") or body)[:4]

    evidence = _bullets(sections.get(evidence_key, "")) if evidence_key else []
    if not evidence:
        evidence = _paragraphs(sections.get(evidence_key, ""))[:4]

    why = sections.get(why_key, "") if why_key else ""
    if not why:
        why = (_paragraphs(body)[0] if _paragraphs(body) else "")

    return {
        "id": f"pull-{number}",
        "title": str(pull.get("title") or f"Pull request {number}"),
        "source": f"Pull request #{number} - {author}",
        "origin": {
            "kind": "pull request",
            "number": number,
            "url": str(pull.get("url") or ""),
            "author": author,
            "branch": str(pull.get("headRefName") or ""),
            "repoId": repo_ident,
            "updated": str(pull.get("updatedAt") or ""),
        },
        "why": why,
        "changes": changes,
        "evidence": evidence,
        "unchanged": sections.get(unchanged_key, "") if unchanged_key else "",
        "recommendation": "",
        "tradeoffs": [],
        "file": str(pull.get("headRefName") or ""),
        "comments": [
            {
                "author": ((one.get("author") or {}) or {}).get("login") or "",
                "when": str(one.get("createdAt") or ""),
                "body": str(one.get("body") or ""),
            }
            for one in (pull.get("comments") or [])
        ],
    }


PULL_FIELDS = "number,title,body,author,url,updatedAt,headRefName,isDraft"
PULL_FIELDS_ONE = "number,title,body,author,url,updatedAt,headRefName,comments"


def read_pulls(repo: Path, repo_ident: str) -> tuple[list[dict], str]:
    """Every open pull request on this repository, as proposals."""
    found, why = _json(repo, ["pr", "list", "--state", "open", "--limit", str(PULL_LIMIT), "--json", PULL_FIELDS])
    if why:
        return [], why
    return [proposal_from_pull(one, repo_ident) for one in (found or [])], ""


def read_pull(repo: Path, repo_ident: str, number: int) -> tuple[dict, str]:
    """One pull request and the conversation on it."""
    found, why = _json(repo, ["pr", "view", str(number), "--json", PULL_FIELDS_ONE])
    if why:
        return {}, why
    if not found:
        return {}, f"the host knows no pull request #{number} in {repo_ident}"
    return proposal_from_pull(found, repo_ident), ""


# --------------------------------------------------------------------------
# clause 4 -- a question reaches the host as a comment
# --------------------------------------------------------------------------
def post_comment(repo: Path, number: int, body: str) -> dict:
    """Put one comment on a pull request, using the host's own command line."""
    said = (body or "").strip()
    if not said:
        return {"ok": False, "reason": "a comment with nothing in it is not sent"}
    ok, out, why = _run(repo, [*COMMENT_ARGV[1:], str(number), "--body", said])
    if not ok:
        return {"ok": False, "reason": why, "number": number}
    return {"ok": True, "number": number, "posted": said, "url": (out or "").strip()}


def answer_words(decision: str, note: str, user: str) -> str:
    """The comment a decision becomes, in the steward's own words first."""
    word = DECISION_WORDS.get(decision, decision or "Recorded")
    lines = [f"**{word}** - the steward answered in Converge."]
    if (note or "").strip():
        lines += ["", (note or "").strip()]
    if user:
        lines += ["", f"_Answered by {user}, recorded in this repository's dated ratification record._"]
    return "\n".join(lines)


def post_answer_back(repo: Path, number: int, decision: str, note: str, user: str) -> dict:
    """Send the steward's word to the origin the proposal came from."""
    return post_comment(repo, number, answer_words(decision, note, user))


# --------------------------------------------------------------------------
# clause 6 -- inbound changes arrive without the steward asking
# --------------------------------------------------------------------------
class Arrivals:
    """When the host last called, in memory, per repository.

    In memory on purpose: this is a liveness fact about the last few minutes,
    and a restart that forgot it should go back to saying `polling` rather than
    claim a webhook nobody has heard from.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last: dict[str, float] = {}
        self._events: list[dict] = []

    def record(self, repo_ident: str, event: str, said: str = "") -> dict:
        now = time.time()
        with self._lock:
            self._last[repo_ident or "*"] = now
            entry = {"repoId": repo_ident, "event": event, "at": _stamp(now), "note": said}
            self._events.append(entry)
            del self._events[:-20]
        return entry

    def last(self, repo_ident: str = "") -> float:
        with self._lock:
            if repo_ident and repo_ident in self._last:
                return self._last[repo_ident]
            return max(self._last.values()) if self._last else 0.0

    def recent(self) -> list[dict]:
        with self._lock:
            return list(reversed(self._events))


ARRIVALS = Arrivals()


def _stamp(when: float) -> str:
    return datetime.fromtimestamp(when, timezone.utc).astimezone().isoformat(timespec="seconds")


def freshness(repo_ident: str = "") -> dict:
    """How this surface stays current, said in words a steward reads.

    Clause 6 asks for two things and this answers both: something brings a
    change in without the steward acting, and the surface says which something
    it is rather than leaving them to guess.
    """
    last = ARRIVALS.last(repo_ident)
    told = bool(last) and (time.time() - last) < WEBHOOK_FRESH_SECONDS
    if told:
        words = (
            f"Webhook - the host called this app at {_stamp(last)}, so changes arrive as "
            f"they happen. Polling still runs every {POLL_SECONDS} seconds behind it."
        )
    else:
        words = (
            f"Polling - checked every {POLL_SECONDS} seconds. No webhook call has arrived "
            "from the host, so this app asks rather than waiting to be told. Either way "
            "you are not the one keeping this fresh."
        )
    return {
        "ok": True,
        "mechanism": "webhook" if told else "polling",
        "seconds": POLL_SECONDS,
        "words": words,
        "lastArrival": _stamp(last) if last else "",
        "webhookPath": WEBHOOK_PATH,
        "recent": ARRIVALS.recent()[:5],
    }


def shared_secret() -> str:
    try:
        return SECRET_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


# --------------------------------------------------------------------------
# resolving what the request is about
# --------------------------------------------------------------------------
def _settings(request: Request) -> config.AppConfig:
    return config.load(getattr(request.app.state, "config_path", None))


def _manager(request: Request, mid: str):
    return _settings(request).manager(mid)


def steward_of(mc) -> str:
    """Whose word counts on this manager session, settled at registration.

    Clause 8 asks for this to be a fact about the registered session rather
    than an inference from whoever is signed in. `ManagerConfig` does not carry
    the field yet -- adding it is `app/config.py` and `app/data.py`, which this
    lane does not own -- so this reads it when it is there and says nothing
    when it is not. It never falls back to the reader.
    """
    return str(getattr(mc, "steward", "") or "")


def _repo_for(mc, repo_ident: str):
    for one in mc.repos:
        if data.repo_id(one) == repo_ident:
            return one
    return mc.repo


def _who(request: Request) -> str:
    return getattr(request.state, "user", "") or ""


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------
@router.get("/{mid}/pulls")
def list_pulls(mid: str, request: Request) -> JSONResponse:
    """Every open pull request on this session's repositories, as proposals."""
    mc = _manager(request, mid)
    if mc is None:
        return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
    proposals: list[dict] = []
    trouble: list[dict] = []
    for repo in mc.repos:
        repo_ident = data.repo_id(repo)
        found, why = read_pulls(Path(repo), repo_ident)
        if why:
            trouble.append({"repoId": repo_ident, "reason": why})
            continue
        proposals.extend(found)
    return JSONResponse({
        "ok": True,
        "proposals": proposals,
        "limit": PULL_LIMIT,
        "unreadable": trouble,
        "steward": steward_of(mc),
        "freshness": freshness(),
    })


@router.get("/{mid}/pulls/{number}")
def one_pull(mid: str, number: int, request: Request, repoId: str = "") -> JSONResponse:
    """One pull request laid out as a proposal, with its conversation."""
    mc = _manager(request, mid)
    if mc is None:
        return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
    repo = _repo_for(mc, repoId)
    if repo is None:
        return JSONResponse({"error": "this manager session has no repository to read"}, status_code=400)
    found, why = read_pull(Path(repo), data.repo_id(repo), number)
    if why:
        return JSONResponse({"ok": False, "reason": why}, status_code=502)
    return JSONResponse({"ok": True, "proposal": found, "freshness": freshness(data.repo_id(repo))})


@router.post("/{mid}/pulls/{number}/comments")
async def ask_on_the_host(mid: str, number: int, request: Request) -> JSONResponse:
    """A question asked in Converge, arriving on the host as a comment."""
    mc = _manager(request, mid)
    if mc is None:
        return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
    try:
        body = await request.json()
    except Exception:
        body = {}
    body = body if isinstance(body, dict) else {}
    repo = _repo_for(mc, str(body.get("repoId") or ""))
    if repo is None:
        return JSONResponse({"error": "this manager session has no repository to ask in"}, status_code=400)
    said = str(body.get("text") or "").strip()
    if not said:
        return JSONResponse({"ok": False, "reason": "a question with nothing in it is not sent"}, status_code=400)
    who = _who(request)
    signed = f"{said}\n\n_Asked by {who} from Converge._" if who else said
    result = post_comment(Path(repo), number, signed)
    return JSONResponse(result, status_code=200 if result.get("ok") else 502)


@router.post("/{mid}/pulls/{number}/answer")
async def answer_a_pull(mid: str, number: int, request: Request) -> JSONResponse:
    """The steward's word: into the dated record, and back to its origin.

    Both halves of clause 5, in one action, and each reported separately so a
    host that refuses the comment never makes the record look unwritten.
    """
    mc = _manager(request, mid)
    if mc is None:
        return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
    try:
        body = await request.json()
    except Exception:
        body = {}
    body = body if isinstance(body, dict) else {}
    repo = _repo_for(mc, str(body.get("repoId") or ""))
    if repo is None:
        return JSONResponse({"error": "this manager session has no repository to record against"}, status_code=400)
    decision = str(body.get("decision") or "")
    if decision not in DECISION_WORDS:
        return JSONResponse(
            {"ok": False, "reason": f"the four words are {sorted(DECISION_WORDS)}; {decision or 'nothing'} is not one"},
            status_code=400,
        )
    note = str(body.get("note") or "")
    who = _who(request)
    recorded = writes.record_decision(
        Path(repo),
        repo_id=data.repo_id(repo),
        doc_id=str(body.get("docId") or f"pull-{number}"),
        proposal_id=f"pull-{number}",
        decision=decision,
        note=note,
        user=who,
    )
    returned = post_answer_back(Path(repo), number, decision, note, who)
    return JSONResponse({
        "ok": bool(recorded.get("ok")),
        "decision": DECISION_WORDS[decision],
        "recorded": recorded,
        "returnedToOrigin": returned,
        "origin": {"kind": "pull request", "number": number, "repoId": data.repo_id(repo)},
    })


@router.post("/webhooks/host")
async def host_called(request: Request) -> JSONResponse:
    """The door the host knocks on when something changed.

    It is checked against a shared secret so anything that reaches this route
    still has to prove it is the host. When no secret file exists the route
    refuses rather than trusting the caller.
    """
    wanted = shared_secret()
    given = request.headers.get("x-converge-secret", "")
    if not wanted:
        return JSONResponse(
            {"ok": False, "reason": f"no shared secret is set, so a call cannot be told from anyone else ({SECRET_PATH})"},
            status_code=503,
        )
    if given != wanted:
        return JSONResponse({"ok": False, "reason": "that call did not carry this app's shared secret"}, status_code=403)
    try:
        body = await request.json()
    except Exception:
        body = {}
    body = body if isinstance(body, dict) else {}
    entry = ARRIVALS.record(
        str(body.get("repoId") or body.get("repository") or ""),
        str(request.headers.get("x-github-event") or body.get("event") or "change"),
        str(body.get("note") or ""),
    )
    return JSONResponse({"ok": True, "arrival": entry, "freshness": freshness()})


@router.get("/{mid}/freshness")
def how_it_stays_fresh(mid: str, request: Request, repoId: str = "") -> JSONResponse:
    """What the surface prints about how current it is."""
    mc = _manager(request, mid)
    if mc is None:
        return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
    return JSONResponse({**freshness(repoId), "steward": steward_of(mc)})
