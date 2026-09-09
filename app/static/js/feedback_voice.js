// Feedback as a voice note — the browser half of `experience-operation.v1`
// clause 10 ("Text, a screenshot, or voice"), landing beside the text in the
// project's `.converge/feedback/` folder (converge-rj1).
//
// One gesture, three forms. This module owns only the third: the field the
// feedback dialog grows, the recording it makes when the browser can record,
// and the one POST that carries it. `actions.js` still sends the text and the
// screenshot exactly as it did; the recording follows on the same press of
// "Send feedback", named after the note the server just wrote, so the two land
// as one piece of feedback rather than two.
//
// ## Why this is a module and not a section of `actions.js`
//
// It was written as this file, folded back into `actions.js` before it
// shipped, and split back out here (converge-s7e9). The fold-back was not
// taste: `app/static/sw.js` names every client module by hand in `PRECACHE`,
// and `app/tests/test_web_polish.py` derives what the app actually loads by
// walking `main.js`'s import graph, so a new module is a new PRECACHE entry or
// it is a module a steward loses the moment they go offline — along with
// everything that imports it. Measured before the entry was added:
//
//     MISSING /static/js/feedback_voice.js
//     FAILED app/tests/test_web_polish.py::
//         test_the_precache_list_carries_every_module_the_app_loads
//
// `cache.addAll` is all-or-nothing and `sw.js` swallows its rejection, so the
// symptom would have been an app that silently stops opening offline rather
// than a missing voice note. The two files move together or neither moves.
//
// ## Recording is not always available, and the sentence says which
//
// `MediaRecorder` and `navigator.mediaDevices` are two different absences and
// they are said differently. `mediaDevices` is undefined outside a secure
// context, which on this app is the ordinary LAN case — served over plain
// http from `your-hostname:8788`, no browser will hand over a microphone. That is
// not a defect to hide behind a dead button: the field says so in a plain
// sentence and offers the file input, which works everywhere and always has.
// `experience.v1` Core 14 asks a body to say what it cannot do; this says it
// at the exact control it is about.
//
// The file input is therefore never conditional. Recording is the convenience;
// attaching is the floor.

const RECORD_MIME_CANDIDATES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/ogg',
  'audio/mp4',
];

//: Why this browser will not record, in words a steward can act on — or '' when
//: it will. Read once when the field is drawn, never guessed at afterwards.
function whyNoRecording() {
  if (typeof window === 'undefined') return 'there is no browser here to record with';
  if (typeof window.MediaRecorder === 'undefined') {
    return 'this browser cannot record audio';
  }
  if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== 'function') {
    return 'recording needs a secure connection (https, or the app opened on this machine)';
  }
  return '';
}

function pickMime() {
  if (typeof window.MediaRecorder?.isTypeSupported !== 'function') return '';
  return RECORD_MIME_CANDIDATES.find((m) => window.MediaRecorder.isTypeSupported(m)) || '';
}

function asDataUrl(blob) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : null);
    reader.onerror = () => resolve(null);
    reader.readAsDataURL(blob);
  });
}

// --------------------------------------------------------------------------
// the field
// --------------------------------------------------------------------------

//: The markup the feedback dialog grows. `accept="audio/*"` is the offer the
//: conformance kit reads (`conformance/experience/run.py` FEEDBACK_FORMS), and
//: it is here rather than in a template because the image offer it sits beside
//: is here too — the feedback dialog is built in `actions.js`, not in
//: `app/templates/dialogs.html`.
export function voiceField() {
  const why = whyNoRecording();
  const control = why
    ? `<p class="voice-unavailable">Recording is not available here — ${why}. Attach an audio file instead.</p>`
    : '<div class="voice-row"><button type="button" id="feedbackVoiceRecord" class="outline-button voice-record">Record</button>'
      + '<span id="feedbackVoiceState" class="voice-state" role="status" aria-live="polite">Nothing recorded yet.</span></div>';
  return `
      <div class="dialog-field voice-field">
        <label for="feedbackVoice">Or a voice note</label>
        ${control}
        <input id="feedbackVoice" type="file" accept="audio/*" />
      </div>`;
}

// --------------------------------------------------------------------------
// recording
// --------------------------------------------------------------------------

//: Wire the record button and hand back the one thing the caller needs: what
//: the steward left behind, whichever way they left it. Safe to call when the
//: field drew no button — `take()` then reads the file input alone.
export function wireVoiceField(root = document) {
  const button = root.getElementById
    ? root.getElementById('feedbackVoiceRecord')
    : root.querySelector('#feedbackVoiceRecord');
  const state = root.getElementById
    ? root.getElementById('feedbackVoiceState')
    : root.querySelector('#feedbackVoiceState');
  const input = root.getElementById
    ? root.getElementById('feedbackVoice')
    : root.querySelector('#feedbackVoice');

  let recorder = null;
  let chunks = [];
  let recorded = null;
  let stream = null;
  let startedAt = 0;

  const say = (words) => { if (state) state.textContent = words; };

  function releaseTheMicrophone() {
    if (stream) stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }

  async function start() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      say(`The microphone was not allowed, so nothing was recorded (${err.name || err.message}). Attach an audio file instead.`);
      return;
    }
    const mime = pickMime();
    try {
      recorder = new window.MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
    } catch (err) {
      releaseTheMicrophone();
      say(`This browser refused to start a recording (${err.message}). Attach an audio file instead.`);
      return;
    }
    chunks = [];
    recorded = null;
    startedAt = Date.now();
    recorder.addEventListener('dataavailable', (e) => { if (e.data && e.data.size) chunks.push(e.data); });
    recorder.addEventListener('stop', () => {
      releaseTheMicrophone();
      const seconds = Math.max(1, Math.round((Date.now() - startedAt) / 1000));
      recorded = chunks.length ? new Blob(chunks, { type: recorder.mimeType || mime || 'audio/webm' }) : null;
      if (button) button.textContent = 'Record';
      say(recorded
        ? `Recorded ${seconds}s — it will be sent with your feedback.`
        : 'Nothing was captured, so there is no recording to send.');
    });
    recorder.start();
    if (button) button.textContent = 'Stop';
    say('Recording… press Stop when you are done.');
  }

  function stop() {
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    else releaseTheMicrophone();
    recorder = null;
  }

  if (button) {
    button.addEventListener('click', () => {
      if (recorder && recorder.state !== 'inactive') stop();
      else start();
    });
  }

  return {
    //: What the steward left, as the server takes it — or null when they left
    //: nothing. A recording wins over an attached file only because it is the
    //: thing they just made; the file is still read when there is no recording.
    async take() {
      if (recorder && recorder.state !== 'inactive') stop();
      if (recorded) {
        const dataUrl = await asDataUrl(recorded);
        return dataUrl ? { dataUrl, how: 'recorded' } : null;
      }
      const file = input && input.files && input.files[0];
      if (!file) return null;
      const dataUrl = await asDataUrl(file);
      return dataUrl ? { dataUrl, how: 'attached', filename: file.name } : null;
    },
    stop,
    whyNoRecording: whyNoRecording(),
  };
}

// --------------------------------------------------------------------------
// the write
// --------------------------------------------------------------------------

//: `POST /api/managers/{mid}/feedback/voice` — the *drop feedback* write, told
//: which form arrived. It is not a sixth write: `app/feedback_voice.py` says
//: at length why the form is a path parameter and what would have gone wrong
//: had it been a route of its own.
//
// The fetch is here rather than in `api.js` because `api.js` was another lane's
// file when this was written. It obeys the same two rules that file does: send
// the cookie, and carry the server's own refusal out with the error rather than
// a status code.
export async function sendVoiceNote(mid, payload) {
  const res = await fetch(`/api/managers/${encodeURIComponent(mid)}/feedback/voice`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let said = '';
    try {
      const body = await res.json();
      said = (body && (body.error || body.detail)) || '';
    } catch { /* the refusal was not JSON: the status is all there is */ }
    const refusal = new Error(said || `the voice note was refused (${res.status})`);
    refusal.status = res.status;
    throw refusal;
  }
  return res.json();
}

