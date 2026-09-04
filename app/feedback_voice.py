"""Feedback dropped as a voice note — the third form, beside text and a screenshot.

`experience-operation.v1` clause 10: *"Feedback can be dropped in seconds, in
whatever form is to hand. **(IDIOM)** Text, a screenshot, or voice."* `IDIOM`
means the behaviour is required and its shape is not (`experience.v1` Core 10),
so this body may choose the gesture but not drop the form. It used to drop it:
the dialog took `#feedbackText` and `#feedbackImage accept="image/*"`, nothing
anywhere took `audio/*`, and the app said so rather than being silent about it
(converge-9mq). Saying a limit is not closing it. This closes it (converge-rj1).

## This is the feedback write, not a sixth one

`experience.v1` Core 4 fixes the app at five writes and says nothing else, in
any body, writes anything. A voice note is not a sixth write — it is the same
*drop feedback* write with the form it arrived in named in the path:

    POST /api/managers/{mid}/feedback/{form}

The form is a path parameter on purpose, and the whole design turns on that.
`conformance/experience/run.py` reads a route's write by its last segment that
is not a path parameter (`write_tail`), so this route's write is `feedback` —
the third of the five — and rules 4a, 4b and 12 go on reading five writes and
no more. A route ending `/feedback/voice` would have declared a write called
`voice` that no contract names, and rule 12 would have been right to call it
debt. The shape follows the clause: one write, several forms.

## What arrives is what lands

The clause says the folder "takes whatever form it arrives in", so this never
transcodes and never renames a format. The extension comes from the MIME type
the browser recorded with — `audio/webm;codecs=opus` lands as `.webm`, an
attached `audio/mpeg` file lands as `.mp3` — and an unrecognised audio subtype
lands under its own subtype rather than being guessed into a lie.

Anything that is not `audio/*` is refused in plain words and **nothing is
written**. A refusal writes no file, touches no note, and says which form it
was handed.

## Beside the text, not instead of it

One gesture drops one piece of feedback. `app/writes.py:record_feedback` has
already written `<stamp>.md` (and `<stamp>.png` for a screenshot) by the time
this route is called, so the note names the moment; this writes `<stamp>.webm`
beside it and adds one line to that note's front matter — `voice: <name>` —
exactly as the image half already does. Called with no note to sit beside, it
writes its own, rather than dropping the recording on the floor.

## Wiring

This is an `APIRouter`, and `app/serve.py` is another lane's file today, so the
one line that mounts it —

    from . import feedback_voice
    app.include_router(feedback_voice.router)

— is added there by the session that owns it. Until it is, this module is
inert: no route, and the rest of the app runs unchanged. The sign-in gate in
`app/serve.py` is middleware rather than a per-route dependency, so this route
is behind it the moment it is mounted, without anyone remembering to decorate
it.
"""

from __future__ import annotations

import base64
import binascii
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from . import config

router = APIRouter()

#: The forms this route takes today. Text and a screenshot arrive on the
#: feedback route itself (`app/writes.py:record_feedback`); this is the third.
FORMS = ("voice",)

#: How large a voice note may be before this refuses it. A recording is minutes
#: of speech, not a media library — and a base64 body is read whole into memory
#: before anything is written, so the bound is stated rather than discovered.
MAX_BYTES = 25 * 1024 * 1024

#: `data:audio/webm;codecs=opus;base64,<payload>` — the shape MediaRecorder and
#: a FileReader both produce. The media type is kept whole so the parameters
#: (`;codecs=opus`) can be dropped deliberately rather than by accident.
DATA_URL_RE = re.compile(r"^data:(?P<media>[^,;]+)(?P<params>;[^,]*)?;base64,(?P<payload>.*)$", re.S)

#: The extension each audio type is known by. A type absent from here is not an
#: error — its own subtype becomes the extension, because the clause asks for
#: the form it arrived in and a subtype is that form's name.
KNOWN_EXTENSIONS = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/opus": "opus",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/aac": "aac",
    "audio/wav": "wav",
    "audio/wave": "wav",
    "audio/x-wav": "wav",
    "audio/flac": "flac",
    "audio/x-flac": "flac",
    "audio/3gpp": "3gp",
}

#: What `record_feedback` names a note: `2026-09-04T12-07-46.md`, and nothing
#: else. A note name is matched against this before it is joined to a path, so
#: a name carrying a separator or a parent reference is refused by shape rather
#: than by a scan for the tricks anyone happened to think of.
NOTE_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.md$")


def _refuse(said: str, status: int = 400) -> JSONResponse:
    """A refusal in plain words, and no file written.

    The client reads `error` (`app/static/js/api.js` carries it out with the
    exception), so the sentence a steward is shown is this one.
    """
    return JSONResponse({"ok": False, "error": said}, status_code=status)


def extension_for(media_type: str) -> str:
    """The extension this audio arrived as — never a guess at what it should be."""
    known = KNOWN_EXTENSIONS.get(media_type)
    if known:
        return known
    subtype = media_type.split("/", 1)[1] if "/" in media_type else ""
    cleaned = re.sub(r"[^a-z0-9]+", "", subtype.lower().removeprefix("x-"))
    return cleaned or "audio"


def name_the_voice_note(note_text: str, voice_name: str) -> str | None:
    """`note_text` with `voice: <name>` in its front matter, or None if it has none.

    None is a real answer and the caller reports it: a note whose front matter
    this cannot find is left exactly as it was, because half-writing somebody
    else's file is worse than saying the line could not be added.
    """
    if not note_text.startswith("---\n"):
        return None
    closing = note_text.find("\n---\n", 3)
    if closing == -1:
        return None
    head = note_text[: closing + 1]
    tail = note_text[closing + 1:]
    return f"{head}voice: {voice_name}\n{tail}"


@router.post("/api/managers/{mid}/feedback/{form}")
async def feedback_in_this_form(mid: str, form: str, request: Request) -> JSONResponse:
    """Drop feedback in one more form than text and a screenshot.

    The same write as `/api/managers/{mid}/feedback`, told which form the
    steward had to hand. See this module's docstring for why the form is a path
    parameter and not a route of its own.
    """
    form = (form or "").strip().lower()
    if form not in FORMS:
        return _refuse(
            f"feedback cannot be dropped as {form!r} here — this takes "
            + " and ".join(FORMS)
            + ", and text and a screenshot arrive on the feedback route itself"
        )

    found = config.load(getattr(request.app.state, "config_path", None)).manager(mid)
    if found is None:
        return _refuse(f"no manager named {mid}", 404)
    repo = found.repo
    if repo is None:
        return _refuse("this manager has no repository to write into")

    body = await request.json()
    data_url = str(body.get("dataUrl") or "").strip()
    if not data_url:
        return _refuse("no voice note arrived, so nothing was written")

    match = DATA_URL_RE.match(data_url)
    if not match:
        return _refuse(
            "that voice note did not arrive as an audio recording this can read, "
            "so nothing was written"
        )
    media_type = match.group("media").strip().lower()
    if not media_type.startswith("audio/"):
        return _refuse(
            f"feedback as voice takes an audio recording, and that arrived as "
            f"{media_type} — nothing was written"
        )

    try:
        audio = base64.b64decode(match.group("payload"), validate=True)
    except (binascii.Error, ValueError):
        return _refuse("that voice note could not be decoded, so nothing was written")
    if not audio:
        return _refuse("that voice note arrived empty, so nothing was written")
    if len(audio) > MAX_BYTES:
        return _refuse(
            f"that voice note is {len(audio) // (1024 * 1024)}MB and this takes at most "
            f"{MAX_BYTES // (1024 * 1024)}MB — nothing was written"
        )

    folder = Path(repo) / ".converge" / "feedback"
    note_name = str(body.get("note") or "").strip()
    if note_name and not NOTE_NAME_RE.match(note_name):
        return _refuse(
            f"{note_name!r} is not the name of a feedback note, so nothing was written"
        )

    note_path = folder / note_name if note_name else None
    if note_path is not None and not note_path.is_file():
        # The note is gone or was never there. The recording is still the
        # steward's, so it lands under its own moment rather than being lost
        # to a name that no longer means anything.
        note_path = None

    stem = note_path.stem if note_path is not None else datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    voice_name = f"{stem}.{extension_for(media_type)}"

    try:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / voice_name).write_bytes(audio)
    except OSError as exc:
        return _refuse(f"the voice note could not be written: {exc}")

    named_in_the_note = False
    why_not = ""
    if note_path is None:
        note_path = folder / f"{stem}.md"
        when = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            note_path.write_text(
                "---\n"
                f"context: {str(body.get('context') or '').strip() or 'unspecified'}\n"
                f"user: {getattr(request.state, 'user', '') or 'unknown'}\n"
                f"time: {when}\n"
                f"voice: {voice_name}\n"
                "---\n\n"
                f"{str(body.get('text') or '').strip()}\n",
                encoding="utf-8",
            )
            named_in_the_note = True
        except OSError as exc:
            why_not = f"the note beside it could not be written: {exc}"
    else:
        try:
            renamed = name_the_voice_note(note_path.read_text(encoding="utf-8"), voice_name)
        except OSError as exc:
            renamed, why_not = None, f"the note could not be read: {exc}"
        if renamed is None:
            why_not = why_not or (
                f"{note_path.name} carries no front matter to name the recording in, "
                "so it was left as it was"
            )
        else:
            try:
                note_path.write_text(renamed, encoding="utf-8")
                named_in_the_note = True
            except OSError as exc:
                why_not = f"the note could not be written: {exc}"

    return JSONResponse({
        "ok": True,
        "form": form,
        "path": str(folder / voice_name),
        "voice": voice_name,
        "note": str(note_path),
        "namedInTheNote": named_in_the_note,
        "whyNot": why_not,
        "mediaType": media_type,
        "bytes": len(audio),
    })


__all__ = ["router", "FORMS", "MAX_BYTES", "extension_for", "name_the_voice_note"]
