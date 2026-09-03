/* Amplifier Converge — the shape of the app.
   One page. Two places. One console pane that stays with you across both. */

(() => {
  "use strict";

  const boot = JSON.parse(document.getElementById("boot").textContent || "{}");
  const $ = (id) => document.getElementById(id);
  const body = document.body;

  const state = {
    manager: null,
    place: "direction",
    doc: null,
    docView: "reading",
    consoleOn: false,
    consoleReady: false,
    watching: "",
  };

  // ------------------------------------------------------------ helpers

  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "html") node.innerHTML = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : String(v));
    }
    for (const kid of kids.flat()) {
      if (kid === null || kid === undefined || kid === false) continue;
      node.appendChild(typeof kid === "string" ? document.createTextNode(kid) : kid);
    }
    return node;
  }

  function say(text) {
    const box = $("said");
    box.textContent = text;
    box.classList.add("is-on");
    clearTimeout(say._t);
    say._t = setTimeout(() => box.classList.remove("is-on"), 3600);
  }

  async function post(path, payload) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    return res.json();
  }

  const madeUp = (note) =>
    el("span", { class: "tag tag--made-up" }, "Made up for this proof of concept" + (note ? " — " + note : ""));
  const fromReal = (where) => el("span", { class: "tag" }, "Read from " + where);

  // ------------------------------------------------------------- home

  function drawHome() {
    const cards = $("cards");
    cards.textContent = "";
    for (const manager of boot.managers || []) {
      const badges = [];
      if (manager.needs_you > 0) {
        badges.push(el("span", { class: "badge badge--you" },
          manager.needs_you === 1 ? "1 needs your word" : manager.needs_you + " need your word"));
      } else {
        badges.push(el("span", { class: "badge" }, "Quiet"));
      }
      if (manager.running) {
        const intended = manager.intended ? " of " + manager.intended + " intended" : "";
        badges.push(el("span", { class: "badge" }, manager.running + " running" + intended));
      }
      cards.appendChild(el("button", {
        class: "card", type: "button", onclick: () => openManager(manager),
      },
        el("h2", {}, manager.name),
        el("p", { class: "card__line" }, badges),
        manager.last_line ? el("p", { class: "card__last" }, manager.last_line) : null,
      ));
    }
    const q = boot.queue || {};
    $("home-foot").textContent = q.real
      ? "Everything on this screen is read from the project as it stands right now."
      : "This project keeps no work queue here yet.";
  }

  function openManager(manager) {
    state.manager = manager;
    $("session-name").textContent = manager.name;
    $("back").hidden = false;
    $("places").hidden = false;
    body.dataset.view = "work";
    goPlace(state.place);
  }

  function goHome() {
    state.manager = null;
    $("session-name").textContent = "Manager Sessions";
    $("back").hidden = true;
    $("places").hidden = true;
    body.dataset.view = "home";
    show("view-home");
  }

  function show(which) {
    for (const id of ["view-home", "view-direction", "view-operation"]) {
      $(id).hidden = id !== which;
    }
  }

  function goPlace(place) {
    state.place = place;
    body.dataset.place = place;
    for (const button of document.querySelectorAll(".place")) {
      button.classList.toggle("is-on", button.dataset.place === place);
    }
    show(place === "operation" ? "view-operation" : "view-direction");
    if (place === "operation") drawOperation();
    else drawDirection();
  }

  // -------------------------------------------------------- direction

  function drawDirection() {
    const host = $("direction");
    host.textContent = "";
    const docs = (boot.documents && boot.documents.documents) || [];
    if (!state.doc && docs.length) state.doc = docs[0].slug;

    const picker = el("div", { class: "pill-row" });
    for (const doc of docs) {
      picker.appendChild(el("button", {
        type: "button",
        class: doc.slug === state.doc ? "is-on" : "",
        onclick: () => { state.doc = doc.slug; drawDirection(); },
      }, doc.title + " · " + doc.word));
    }
    host.appendChild(picker);

    const views = el("div", { class: "pill-row" });
    for (const [key, label] of [["reading", "Reading"], ["changes", "Changes"], ["review", "Review"]]) {
      views.appendChild(el("button", {
        type: "button",
        class: state.docView === key ? "is-on" : "",
        onclick: () => { state.docView = key; drawDirection(); },
      }, label));
    }
    host.appendChild(views);

    const panel = el("div", { class: "block", id: "doc-panel" }, el("p", {}, "Reading…"));
    host.appendChild(panel);

    if (state.docView === "review") drawReview(panel);
    else if (state.docView === "changes") drawChanges(panel);
    else drawReading(panel);
  }

  async function drawReading(panel) {
    const res = await fetch("/api/document/" + encodeURIComponent(state.doc));
    const doc = await res.json();
    panel.textContent = "";
    if (!doc.real) { panel.appendChild(el("p", {}, doc.note || "Nothing to read here.")); return; }
    panel.appendChild(fromReal(doc.path));
    panel.appendChild(el("p", { class: "block__why" },
      "This document is a " + doc.word.toLowerCase() + ". Ask for a proposal on any paragraph."));
    const article = el("article", { class: "doc", html: doc.html });
    for (const node of article.querySelectorAll("[data-anchor]")) {
      const anchor = node.getAttribute("data-anchor");
      node.appendChild(el("button", {
        class: "ask", type: "button", title: "Ask for a proposal on this",
        onclick: (event) => askOn(event.target, doc, anchor, node.textContent || ""),
      }, "ask"));
    }
    panel.appendChild(article);
  }

  function askOn(button, doc, anchor, paragraph) {
    if (button.nextSibling && button.nextSibling.classList &&
        button.nextSibling.classList.contains("ask-form")) {
      button.nextSibling.remove();
      return;
    }
    const input = el("input", { type: "text", placeholder: "What should change here, and why?" });
    const form = el("form", {
      class: "ask-form",
      onsubmit: async (event) => {
        event.preventDefault();
        const out = await post("/api/ask", {
          document: doc.title,
          target: doc.path,
          anchor: anchor,
          paragraph: paragraph.replace(/\s*ask$/, "").trim().slice(0, 400),
          question: input.value,
        });
        form.remove();
        say("Asked. It is waiting for your word under Review, and written to " + out.file + ".");
        const asked = out.record;
        (boot.proposals.proposals = boot.proposals.proposals || []).push({
          key: asked.key, title: asked.title, from: "you asked for this",
          where: "poc/asks.jsonl", target: asked.target,
          change: "<p>Not drafted yet. Your manager session has the request and will bring back a proposal.</p>",
          evidence: "<blockquote>" + asked.paragraph.replace(/[<>&]/g, "") + "</blockquote>",
          not_change: "<p>Nothing changes until you answer with a word.</p>",
          question: asked.question,
        });
      },
    }, input, el("button", { type: "submit" }, "Ask"));
    button.after(form);
    input.focus();
  }

  async function drawChanges(panel) {
    const res = await fetch("/api/changes/" + encodeURIComponent(state.doc));
    const changed = await res.json();
    panel.textContent = "";
    panel.appendChild(fromReal("the last two saved versions of this document"));
    if (!changed.real) { panel.appendChild(el("p", {}, changed.note)); return; }
    panel.appendChild(el("p", { class: "block__why" },
      "Between " + changed.older.when + " and " + changed.newer.when + ". The newer one was saved because: " +
      changed.newer.why));
    if (!changed.added.length && !changed.removed.length) {
      panel.appendChild(el("p", {}, "Nothing in the sentences changed."));
      return;
    }
    if (changed.added.length) {
      panel.appendChild(el("h3", {}, "New sentences"));
      for (const s of changed.added.slice(0, 40)) panel.appendChild(el("p", { class: "was-added" }, s));
    }
    if (changed.removed.length) {
      panel.appendChild(el("h3", {}, "Sentences that went away"));
      for (const s of changed.removed.slice(0, 40)) panel.appendChild(el("p", { class: "was-removed" }, s));
    }
  }

  function drawReview(panel) {
    panel.textContent = "";
    const list = (boot.proposals && boot.proposals.proposals) || [];
    if (!list.length) { panel.appendChild(el("p", {}, "Nothing is waiting for your word.")); return; }
    panel.appendChild(el("p", { class: "block__why" },
      list.length === 1 ? "One thing is waiting for your word." : list.length + " things are waiting for your word."));
    for (const proposal of list.slice(0, 5)) {
      panel.appendChild(drawProposal(proposal));
    }
  }

  function part(heading, html) {
    const body = el("div", { html: html || "<p>Not written yet.</p>" });
    if ((html || "").length > 3500) {
      return el("div", {}, el("h4", {}, heading),
        el("details", {}, el("summary", {}, "All of it — this one is long"), body));
    }
    return el("div", {}, el("h4", {}, heading), body);
  }

  function drawProposal(proposal) {
    const answered = (boot.answers || []).filter((a) => a.proposal === proposal.key).slice(-1)[0];
    const card = el("div", { class: "block" },
      el("span", { class: "tag" }, "From " + proposal.from + (proposal.where ? " · " + proposal.where : "")),
      el("h3", {}, proposal.title),
      proposal.target ? el("p", { class: "block__why" }, "It would change " + proposal.target + ".") : null,
      proposal.question ? el("p", { class: "block__why" }, "You asked: " + proposal.question) : null,
      part("What changes", proposal.change),
      part("The evidence", proposal.evidence),
      part("What does not change", proposal.not_change),
    );
    const said = el("p", { class: "block__why" },
      answered ? "You answered: " + answered.word + " (" + answered.at + ")" : "");
    const words = el("div", { class: "pill-row" });
    for (const word of ["ratified", "ratified with edits", "declined", "later"]) {
      words.appendChild(el("button", {
        type: "button",
        class: answered && answered.word === word ? "is-on" : "",
        onclick: async () => {
          const out = await post("/api/answer", { proposal: proposal.key, title: proposal.title, word });
          if (!out.ok) { say(out.note || "That did not take."); return; }
          (boot.answers = boot.answers || []).push(out.record);
          say("Recorded: " + word + " — written to " + out.file + ".");
          drawDirection();
        },
      }, word[0].toUpperCase() + word.slice(1)));
    }
    card.appendChild(words);
    card.appendChild(said);
    return card;
  }

  // -------------------------------------------------------- operation

  function drawOperation() {
    const host = $("operation");
    host.textContent = "";
    host.appendChild(blockBrief());
    host.appendChild(blockStrategy());
    host.appendChild(blockWaves());
    host.appendChild(blockLanes());
    host.appendChild(blockConfidence());
    host.appendChild(blockFeedback());
    host.appendChild(blockSteer());
  }

  function blockBrief() {
    const brief = boot.brief || {};
    const block = el("div", { class: "block" },
      brief.real ? fromReal(brief.source) : madeUp(""),
      el("h2", {}, "Your return brief"),
      brief.heading ? el("p", { class: "block__why" }, brief.heading) : null,
    );
    if (!brief.real) { block.appendChild(el("p", {}, brief.note || "No brief yet.")); return block; }
    for (const sentence of brief.sentences || []) block.appendChild(el("p", {}, sentence));
    return block;
  }

  function blockStrategy() {
    const strategy = boot.strategy || {};
    const block = el("div", { class: "block" }, madeUp(strategy.note), el("h2", {}, "Today's strategy"));
    for (const para of String(strategy.text || "").split(/\n\s*\n/)) {
      if (para.trim()) block.appendChild(el("p", {}, para.replace(/\s+/g, " ").trim()));
    }
    return block;
  }

  function blockWaves() {
    const waves = boot.waves || {};
    const block = el("div", { class: "block" }, madeUp(waves.note), el("h2", {}, "The plan, in waves"));
    for (const wave of waves.waves || []) {
      const item = el("div", {},
        el("div", { class: "row" },
          el("strong", { class: "row__name" }, wave.name),
          el("span", { class: "row__word badge" }, wave.word)),
        el("p", { class: "block__why" }, wave.why));
      const inner = el("details", {}, el("summary", {}, "The lanes in this wave"));
      for (const lane of wave.lanes || []) {
        inner.appendChild(el("div", { class: "row" },
          el("span", { class: "row__name" }, lane.name),
          el("span", { class: "row__word badge" }, lane.word)));
      }
      item.appendChild(inner);
      block.appendChild(item);
    }
    return block;
  }

  function blockLanes() {
    const board = boot.lanes || {};
    const block = el("div", { class: "block" },
      board.real ? fromReal(board.source) : madeUp(""),
      el("h2", {}, "The lanes"));
    if (!board.real) { block.appendChild(el("p", {}, board.note)); return block; }
    const intended = board.intended ? " Your limit is " + board.intended + "." : "";
    block.appendChild(el("p", { class: "block__why" },
      board.running + (board.running === 1 ? " lane is out." : " lanes are out.") + intended));
    for (const lane of board.lanes || []) {
      const since = lane.minutes_since_write === null ? "" : " · last wrote " + lane.minutes_since_write + "m ago";
      block.appendChild(el("div", { class: "row" },
        el("span", { class: "row__name" }, lane.name, el("span", { class: "block__why" }, since)),
        el("span", { class: "row__word" },
          el("span", {
            class: "badge" + (lane.word.startsWith("Silent") ? " badge--warm" : ""),
          }, lane.word),
          el("button", {
            type: "button",
            onclick: () => { state.watching = lane.name; openConsole(); },
          }, "Watch session"))));
    }
    return block;
  }

  function blockConfidence() {
    const conf = boot.confidence || {};
    const points = conf.points || [];
    const block = el("div", { class: "block" }, madeUp(conf.note), el("h2", {}, "How sure it is, over time"));
    if (points.length) {
      const w = 300, h = 68, pad = 4;
      const step = points.length > 1 ? (w - pad * 2) / (points.length - 1) : 0;
      const xy = points.map((p, i) => [pad + i * step, h - pad - (p.value / 100) * (h - pad * 2)]);
      const d = xy.map(([x, y], i) => (i ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1)).join(" ");
      const svg =
        '<svg class="spark" viewBox="0 0 ' + w + " " + h + '" preserveAspectRatio="none" role="img" ' +
        'aria-label="How sure the manager session has been over time">' +
        '<path d="' + d + '" fill="none" stroke="#5B3CC4" stroke-width="2"/>' +
        xy.map(([x, y]) => '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="2.5" fill="#5B3CC4"/>').join("") +
        "</svg>";
      block.appendChild(el("div", { html: svg }));
      block.appendChild(el("p", {}, conf.sentence || ""));
      const why = el("details", {}, el("summary", {}, "Why it moved"));
      for (const p of points) {
        why.appendChild(el("p", {}, p.when + " — " + p.why));
      }
      block.appendChild(why);
    }
    return block;
  }

  function blockFeedback() {
    const area = el("textarea", { placeholder: "Still not working on my phone…" });
    const block = el("div", { class: "block" },
      el("h2", {}, "Drop feedback"),
      el("p", { class: "block__why" },
        "Say it however you like. Your manager session reads it against the promises and the work in flight, and brings you a decision rather than a ticket."),
      area,
      el("button", {
        type: "button",
        onclick: async () => {
          const text = area.value.trim();
          if (!text) { say("Say something first."); return; }
          const out = await post("/api/feedback", { text, about: state.manager ? state.manager.id : "" });
          if (out.ok) { area.value = ""; say("Dropped — written to " + out.file + "."); }
        },
      }, "Drop it"));
    const past = (boot.feedback || []).slice(-3);
    if (past.length) {
      const fold = el("details", {}, el("summary", {}, "What you dropped before"));
      for (const f of past) fold.appendChild(el("p", {}, f.at + " — " + f.text));
      block.appendChild(fold);
    }
    return block;
  }

  function blockSteer() {
    const block = el("div", { class: "block" },
      el("h2", {}, "Steer"),
      el("p", { class: "block__why" }, "Your limits. Stopping is never a button on a board."));
    const controls = [
      ["Lanes at once", ["2", "3", "5", "8"]],
      ["Budget", ["until done", "until a time", "until a spend"]],
      ["Fill", ["keep them full", "let them drain"]],
    ];
    for (const [what, options] of controls) {
      const chosen = (boot.steers || []).filter((s) => s.what === what).slice(-1)[0];
      const row = el("div", {}, el("span", { class: "tag" }, what));
      const pills = el("div", { class: "pill-row" });
      for (const value of options) {
        pills.appendChild(el("button", {
          type: "button",
          class: chosen && chosen.value === value ? "is-on" : "",
          onclick: async () => {
            const out = await post("/api/steer", { what, value });
            if (out.ok) {
              (boot.steers = boot.steers || []).push(out.record);
              say(what + ": " + value + " — written to " + out.file + ".");
              drawOperation();
            }
          },
        }, value));
      }
      row.appendChild(pills);
      block.appendChild(row);
    }
    block.appendChild(el("button", {
      type: "button",
      onclick: async () => {
        const out = await post("/api/steer", { what: "Ask the manager to review", value: "the console pane" });
        if (out.ok) say("Asked it to review the console pane — written to " + out.file + ".");
      },
    }, "Ask it to review something"));
    return block;
  }

  // ---------------------------------------------------------- console

  let term = null;
  let pre = null;

  function paneWrite(text) {
    if (term) { term.write(text); return; }
    if (!pre) {
      pre = el("pre", {});
      $("tray-screen").appendChild(pre);
    }
    pre.textContent += text.replace(/\x1b\[[0-9;]*m/g, "").replace(/\r\n/g, "\n");
    pre.scrollTop = pre.scrollHeight;
  }

  function makePane() {
    const screen = $("tray-screen");
    if (window.Terminal) {
      try {
        const box = screen.getBoundingClientRect();
        const cols = Math.max(28, Math.floor((box.width - 14) / 7.3));
        const rows = Math.max(8, Math.floor((box.height - 12) / 17));
        term = new window.Terminal({
          cols, rows, fontSize: 12, lineHeight: 1.42, convertEol: true,
          fontFamily: 'ui-monospace, "SF Mono", Menlo, Consolas, monospace',
          theme: { background: "#17150F", foreground: "#EFE7DA", cursor: "#9C86E8" },
        });
        term.open(screen);
        return "a real terminal pane";
      } catch (err) {
        term = null;
      }
    }
    return "a plain text pane";
  }

  async function attachConsole() {
    if (state.consoleReady) return;
    state.consoleReady = true;
    const kind = makePane();
    const res = await fetch("/api/console/" + encodeURIComponent("your manager session"));
    const stream = await res.json();
    $("tray-sub").textContent =
      (state.watching ? "Watching " + state.watching + " · " : "") + "A recorded session, shown in " + kind + ".";
    for (const chunk of stream.chunks) paneWrite(chunk);
  }

  function openConsole() {
    state.consoleOn = true;
    body.classList.add("console-open");
    $("console").setAttribute("aria-hidden", "false");
    $("console-toggle").setAttribute("aria-expanded", "true");
    attachConsole();
    if (state.watching && state.consoleReady) {
      $("tray-sub").textContent = "Watching " + state.watching + " · a recorded session.";
    }
  }

  function closeConsole() {
    state.consoleOn = false;
    body.classList.remove("console-open");
    $("console").setAttribute("aria-hidden", "true");
    $("console-toggle").setAttribute("aria-expanded", "false");
  }

  // ------------------------------------------------------------- wire

  $("back").addEventListener("click", goHome);
  $("console-toggle").addEventListener("click", () => (state.consoleOn ? closeConsole() : openConsole()));
  $("tray-close").addEventListener("click", closeConsole);
  for (const button of document.querySelectorAll(".place")) {
    button.addEventListener("click", () => goPlace(button.dataset.place));
  }
  $("tray-say").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = $("tray-input");
    const keys = input.value.trim();
    if (!keys) return;
    input.value = "";
    const out = await post("/api/console/" + encodeURIComponent("your manager session") + "/keys", { keys });
    for (const chunk of out.chunks || []) paneWrite(chunk);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.consoleOn) closeConsole();
  });

  drawHome();
  goHome();

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
  }

  window.__converge = { state, openConsole, closeConsole, openManager, goPlace, boot };
})();
