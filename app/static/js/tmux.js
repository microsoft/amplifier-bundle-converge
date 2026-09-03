/* app/static/js/tmux.js — the read-only tmux pane viewer.
 *
 * Owner: the tmux lane.  The front end calls exactly two things:
 *
 *     window.ConvergeTmux.attach(el, socket, session)
 *     window.ConvergeTmux.detach()
 *
 * Field guide (ai-context/BROWSER-TMUX-VIEWER.md) rules enforced here:
 *
 *  - xterm.js is **vendored** under /static/vendor/xterm and lazy-loaded from
 *    there.  No CDN, ever.
 *  - One poll every TICK_MS (750 ms): clear() + write() of the captured text.
 *  - The trailing newline is stripped before write(), or a full-height
 *    alt-screen TUI scrolls its title row out of view (§6, a real defect).
 *  - The grid is sized from the pane's own geometry (cols = pane_width,
 *    rows = pane_height); the container overflows sideways rather than wrapping.
 *  - Four states, never conflated, each with its own banner class:
 *    tmux-ok · tmux-empty · tmux-ended · tmux-failed.
 *  - The viewer is bound to a session **identity**.  A frame whose socket or
 *    session does not match what we attached to is dropped on the floor; on
 *    loss we render `ended` and stop.  We never fall through to another
 *    session's pane (§6, the other real defect).
 *  - Read-only in this version: no input, no send-keys.
 */

(function () {
  "use strict";

  var TICK_MS = 750;
  var LINES = 200;
  var FRESHNESS_MS = 250;

  // Where the vendored xterm.js lives.  Overridable so a test harness (or a
  // differently-mounted static dir) can point at it; never a remote origin.
  var VENDOR_BASE = window.CONVERGE_TMUX_VENDOR_BASE || "/static/vendor/xterm";
  var API_BASE = window.CONVERGE_TMUX_API_BASE || "/api/tmux";

  var STATE_LABEL = {
    ok: "live",
    empty: "pane is empty",
    ended: "session ended",
    failed: "observation failed",
  };

  // ---------------------------------------------------------------- vendor

  var _xtermPromise = null;

  function loadStylesheet(href) {
    if (document.querySelector('link[data-converge-tmux="css"]')) return;
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.setAttribute("data-converge-tmux", "css");
    document.head.appendChild(link);
  }

  function loadXterm() {
    if (window.Terminal) return Promise.resolve(window.Terminal);
    if (_xtermPromise) return _xtermPromise;
    loadStylesheet(VENDOR_BASE + "/css/xterm.css");
    _xtermPromise = new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = VENDOR_BASE + "/lib/xterm.js"; // vendored, same origin
      s.async = true;
      s.onload = function () {
        if (window.Terminal) resolve(window.Terminal);
        else reject(new Error("xterm.js loaded but window.Terminal is missing"));
      };
      s.onerror = function () {
        reject(new Error("could not load vendored xterm.js from " + VENDOR_BASE));
      };
      document.head.appendChild(s);
    });
    return _xtermPromise;
  }

  // ------------------------------------------------------------------ dom

  function buildDom(el, socket, session) {
    el.innerHTML = "";
    var root = document.createElement("div");
    root.className = "tmux-view";
    root.setAttribute("data-socket", socket);
    root.setAttribute("data-session", session);

    var banner = document.createElement("div");
    banner.className = "tmux-banner tmux-ok";

    var state = document.createElement("span");
    state.className = "tmux-state";
    state.textContent = "connecting";

    var who = document.createElement("span");
    who.className = "tmux-session";
    who.textContent = socket + " / " + session;

    var fresh = document.createElement("span");
    fresh.className = "tmux-freshness";
    fresh.textContent = "—";

    var ro = document.createElement("span");
    ro.className = "tmux-readonly";
    ro.textContent = "read-only in this version";

    banner.appendChild(state);
    banner.appendChild(who);
    banner.appendChild(fresh);
    banner.appendChild(ro);

    var term = document.createElement("div");
    term.className = "tmux-term";
    // Overflow sideways rather than reflow: the grid is sized from the pane.
    term.style.overflowX = "auto";
    term.style.overflowY = "hidden";

    root.appendChild(banner);
    root.appendChild(term);
    el.appendChild(root);
    return { root: root, banner: banner, state: state, fresh: fresh, term: term };
  }

  function ageText(capturedAt) {
    if (!capturedAt) return "—";
    var t = Date.parse(capturedAt);
    if (isNaN(t)) return "—";
    var secs = (Date.now() - t) / 1000;
    if (secs < 0) secs = 0;
    return secs < 10 ? secs.toFixed(1) + "s ago" : Math.round(secs) + "s ago";
  }

  // ----------------------------------------------------------------- view

  function View(el, socket, session) {
    this.el = el;
    this.socket = socket;
    this.session = session;
    this.dom = buildDom(el, socket, session);
    this.term = null;
    this.timer = null;
    this.freshTimer = null;
    this.controller = null;
    this.stopped = false;
    this.cols = 0;
    this.rows = 0;
    this.lastState = null;
    this.lastCapturedAt = null;
    this.frames = 0;
  }

  View.prototype.start = function () {
    var self = this;
    this.freshTimer = setInterval(function () {
      if (self.dom) self.dom.fresh.textContent = ageText(self.lastCapturedAt);
    }, FRESHNESS_MS);

    loadXterm()
      .then(function (Terminal) {
        if (self.stopped) return;
        self.term = new Terminal({
          convertEol: true, // capture-pane emits bare \n
          disableStdin: true, // read-only in this version
          cursorBlink: false,
          scrollback: 0, // every tick paints the whole captured buffer
          fontSize: 12,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, "DejaVu Sans Mono", monospace',
          theme: { background: "#0b0d10", foreground: "#d8dee9" },
        });
        self.term.open(self.dom.term);
        self.tick();
      })
      .catch(function (err) {
        self.render({ state: "failed", detail: String(err && err.message ? err.message : err) });
      });
  };

  View.prototype.tick = function () {
    if (this.stopped) return;
    var self = this;
    var socket = this.socket;
    var session = this.session;
    var url =
      API_BASE +
      "/" +
      encodeURIComponent(socket) +
      "/" +
      encodeURIComponent(session) +
      "?lines=" +
      LINES;

    this.controller = new AbortController();
    fetch(url, { signal: this.controller.signal, credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (frame) {
        if (self.stopped) return;
        // Identity gate: a frame that is not about the session we attached to
        // is never painted.  This is what stops a silent re-target.
        if (
          (frame.session && frame.session !== session) ||
          (frame.socket && frame.socket !== socket) ||
          session !== self.session ||
          socket !== self.socket
        ) {
          return;
        }
        self.render(frame);
      })
      .catch(function (err) {
        if (self.stopped || (err && err.name === "AbortError")) return;
        self.render({ state: "failed", detail: String(err && err.message ? err.message : err) });
      })
      .then(function () {
        if (self.stopped) return;
        // `ended` is terminal: the session is gone, so stop asking.
        if (self.lastState === "ended") return;
        self.timer = setTimeout(function () {
          self.tick();
        }, TICK_MS);
      });
  };

  View.prototype.render = function (frame) {
    var state = frame.state || "failed";
    this.lastState = state;
    this.frames += 1;
    if (frame.captured_at) this.lastCapturedAt = frame.captured_at;

    // Banner: one distinct class per state, asserted on by the browser tests.
    this.dom.banner.className = "tmux-banner tmux-" + state;
    var label = STATE_LABEL[state] || state;
    if (state === "failed" && frame.detail) label += " — " + frame.detail;
    if (state === "ended") label += " — " + this.session;
    this.dom.state.textContent = label;
    this.dom.fresh.textContent = ageText(this.lastCapturedAt);
    this.dom.root.setAttribute("data-state", state);
    this.dom.root.setAttribute("data-frames", String(this.frames));

    if (!this.term) return;

    var geo = frame.geometry;
    if (geo && geo.width > 0 && geo.height > 0) {
      if (geo.width !== this.cols || geo.height !== this.rows) {
        this.cols = geo.width;
        this.rows = geo.height;
        this.term.resize(this.cols, this.rows); // sized from the pane, not the viewport
      }
      this.dom.root.setAttribute("data-alternate", geo.alternate_on ? "1" : "0");
    }

    if (state === "ok" || state === "empty") {
      // Strip the trailing newline before writing, or a full-height
      // alt-screen TUI scrolls its top row out of view (field guide §6).
      var text = String(frame.text || "").replace(/\n$/, "");
      this.term.reset(); // drop the previous frame's SGR state
      this.term.clear(); // clear() + write() per tick
      this.term.write(text);
    }
    // `ended` / `failed` deliberately leave the last real frame of *this*
    // session on screen.  Nothing from another session is ever written.
  };

  View.prototype.stop = function () {
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
    if (this.freshTimer) clearInterval(this.freshTimer);
    this.timer = null;
    this.freshTimer = null;
    if (this.controller) {
      try {
        this.controller.abort();
      } catch (e) {
        /* ignore */
      }
      this.controller = null;
    }
    if (this.term) {
      try {
        this.term.dispose();
      } catch (e) {
        /* ignore */
      }
      this.term = null;
    }
    if (this.el) this.el.innerHTML = "";
  };

  // ----------------------------------------------------------------- api

  var current = null;

  window.ConvergeTmux = {
    tickMs: TICK_MS,

    attach: function (el, socket, session) {
      if (typeof el === "string") el = document.querySelector(el);
      if (!el) throw new Error("ConvergeTmux.attach: no element");
      if (!socket || !session) throw new Error("ConvergeTmux.attach: socket and session are required");
      this.detach();
      current = new View(el, String(socket), String(session));
      current.start();
      return current;
    },

    detach: function () {
      if (current) {
        current.stop();
        current = null;
      }
    },

    // Honest introspection for tests and for the console: what are we
    // actually looking at, and how old is the frame.
    current: function () {
      if (!current) return null;
      return {
        socket: current.socket,
        session: current.session,
        state: current.lastState,
        captured_at: current.lastCapturedAt,
        frames: current.frames,
        cols: current.cols,
        rows: current.rows,
      };
    },
  };
})();
