"""The look, as one stylesheet served from the page itself.

Mobile first on purpose: the base rules are the 390-pixel layout, and the wider
shell only appears inside a `min-width` query. Nothing carries a fixed pixel
width, every scrollable thing is capped at the width of its parent, and every
grid child is allowed to shrink — which together is what "nothing cut off at
390 pixels" actually means in CSS.

Design direction: a steward's desk. Paper, warm ink, and one accent — the stamp
violet that appears when your word lands on something. Moss and brick appear
only as small status marks, never as fields of colour. Serif for headings so
the documents read as documents; the monospace font appears only inside a
Details fold, where it signals that you have left the plain-language surface.
"""

from __future__ import annotations

WORDMARK = "Amplifier Converge"

STYLESHEET = """
:root{
  --paper:#F2F1EB; --paper-deep:#E9E7DE; --card:#FDFCF9;
  --ink:#23201C; --ink-2:#59544C; --ink-3:#6E6860;
  --rule:#DEDACF; --rule-soft:#EAE7DE;
  --accent:#5A46B4; --accent-ink:#452F9C; --accent-soft:#ECE8FA;
  --moss:#5A7552; --brick:#A4553E; --amber:#8A6D2F;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Charter,Georgia,serif;
  --sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Inter,Roboto,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono","Cascadia Mono",Menlo,Consolas,monospace;
  --r:14px;
  --shadow:0 1px 2px rgba(35,32,28,.05),0 12px 28px -20px rgba(35,32,28,.55);
  --tap:46px;
}

*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0;background:var(--paper);color:var(--ink);
  font-family:var(--sans);font-size:16px;line-height:1.55;
  overflow-wrap:anywhere;word-break:normal;
  -webkit-font-smoothing:antialiased;
}
h1,h2,h3,h4{font-family:var(--serif);font-weight:600;margin:0;line-height:1.22;letter-spacing:-.012em}
p{margin:0}
ul,ol{margin:0;padding:0;list-style:none}
a{color:var(--accent-ink);text-decoration-thickness:1px;text-underline-offset:2px}
img{max-width:100%;height:auto}
:focus-visible{outline:2.5px solid var(--accent);outline-offset:3px;border-radius:8px}

.skip{position:absolute;left:-9999px;top:0;background:var(--card);padding:12px 16px;z-index:99}
.skip:focus{left:0}

/* ---- shell: one column first, two only when there is room ---- */
.shell{display:block;max-width:1180px;margin:0 auto;padding:0 16px 72px}
.rail{
  position:sticky;top:0;z-index:20;background:var(--paper-deep);
  margin:0 -16px 20px;padding:14px 16px 12px;border-bottom:1px solid var(--rule);
}
.brand{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;min-width:0}
.wordmark{font-family:var(--serif);font-size:21px;font-weight:600;letter-spacing:-.02em}
.project{
  font-size:12px;color:var(--ink-2);background:var(--card);border:1px solid var(--rule);
  border-radius:999px;padding:3px 10px;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.places{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
.place{
  display:inline-flex;align-items:center;gap:8px;min-height:var(--tap);
  padding:0 16px;border-radius:999px;border:1px solid var(--rule);
  background:var(--card);color:var(--ink-2);font-weight:600;font-size:14.5px;
  text-decoration:none;
}
.place.is-on{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.place .count{
  min-width:22px;height:22px;padding:0 6px;border-radius:11px;background:var(--accent);
  color:#fff;font-size:11.5px;font-weight:700;display:inline-grid;place-items:center;
}
.place.is-on .count{background:var(--paper);color:var(--ink)}

/* ---- generic surfaces ---- */
.card{
  background:var(--card);border:1px solid var(--rule);border-radius:var(--r);
  padding:18px;margin:0 0 14px;box-shadow:var(--shadow);min-width:0;
}
.lbl{
  display:inline-block;font-size:11px;font-weight:700;letter-spacing:.11em;
  text-transform:uppercase;color:var(--ink-3);
}
.muted{color:var(--ink-2);font-size:14.5px}
.section{margin:26px 0 12px}
.section h2{font-size:22px}
.section p{color:var(--ink-2);font-size:14.5px;margin-top:4px}
.stack > * + *{margin-top:10px}
.rows{display:grid;grid-template-columns:minmax(0,1fr);gap:12px}
.rows > *{min-width:0}

/* ---- the strip ---- */
.strip-empty{
  background:linear-gradient(180deg,var(--card),var(--accent-soft));
  border:1px solid var(--rule);border-radius:var(--r);padding:30px 20px;text-align:center;
}
.strip-empty h2{font-size:26px}
.strip-empty p{margin-top:8px;color:var(--ink-2)}
.decision{border-left:3px solid var(--accent);}
.decision h3{font-size:19px}
.decision .why{margin-top:8px;color:var(--ink-2);font-size:15px}
.decision .rec{
  margin-top:12px;padding:11px 13px;background:var(--accent-soft);
  border-radius:10px;font-size:15px;
}
.tradeoffs{margin-top:12px}
.tradeoffs li{
  position:relative;padding-left:18px;color:var(--ink-2);font-size:14.5px;margin-top:5px;
}
.tradeoffs li::before{content:"—";position:absolute;left:0;color:var(--ink-3)}

/* ---- words: the answer control ---- */
.words{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.word{
  min-height:var(--tap);padding:0 16px;border-radius:10px;border:1px solid var(--rule);
  background:var(--card);color:var(--ink);font:inherit;font-weight:600;font-size:14.5px;
  cursor:pointer;flex:1 1 auto;min-width:0;
}
.word.is-primary{background:var(--accent);border-color:var(--accent);color:#fff}
.word:hover{border-color:var(--accent)}

/* ---- status marks, in words ---- */
.mark{
  display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;
  color:var(--ink-2);white-space:nowrap;
}
.mark::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--ink-3);flex:0 0 8px}
.mark.good::before{background:var(--moss)}
.mark.bad::before{background:var(--brick)}
.mark.warn::before{background:var(--amber)}
.mark.on::before{background:var(--accent)}
.chip{
  display:inline-block;font-size:12px;font-weight:600;color:var(--ink-2);
  background:var(--paper-deep);border:1px solid var(--rule);border-radius:999px;padding:2px 9px;
}
.chip.locked{background:var(--accent-soft);color:var(--accent-ink);border-color:#D8CFF4}
/* whether the promise is being kept — a second signal, beside the first */
.chip.kept{color:var(--moss);border-color:#C7D3C2}
.chip.broken{color:var(--brick);border-color:#E0C3B9}
.chip.open{color:var(--amber);border-color:#DFD0AC}
.chip.unsure{color:var(--ink-3);border-style:dashed}

/* ---- documents ---- */
.doc{max-width:68ch}
.doc h1{font-size:27px;margin-bottom:6px}
.doc h2{font-size:20px;margin-top:26px}
.doc h3{font-size:17px;margin-top:20px}
.doc p, .doc li{font-size:16px;line-height:1.62;color:var(--ink)}
.doc .para{position:relative;margin-top:14px}
.doc .para .ask{
  font-size:12px;color:var(--ink-3);text-decoration:none;border:1px solid var(--rule-soft);
  border-radius:999px;padding:2px 9px;margin-left:6px;white-space:nowrap;
}
.doc pre,pre{
  background:var(--paper-deep);border:1px solid var(--rule);border-radius:10px;
  padding:12px;max-width:100%;overflow-x:auto;font-family:var(--mono);font-size:13px;
}
code{font-family:var(--mono);font-size:.92em}
table{width:100%;max-width:100%;border-collapse:collapse;display:block;overflow-x:auto}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--rule-soft);font-size:14px}

/* ---- quoted: words the page shows but did not write ---- */
.quote{color:inherit}

/* ---- what changed ---- */
.diff li, .doc.diff li{padding:8px 12px;border-radius:9px;margin-top:6px;font-size:14.5px;line-height:1.5}
.diff .added{background:#EEF4EC;border-left:3px solid var(--moss)}
.diff .removed{background:#F7EEEB;border-left:3px solid var(--brick);text-decoration:line-through;color:var(--ink-2)}

/* ---- the lock gate ---- */
.gate li{display:flex;gap:10px;align-items:flex-start;margin-top:9px;font-size:14.5px}
.gate .state{flex:0 0 auto;font-weight:700;font-size:12px;letter-spacing:.06em;text-transform:uppercase}
.gate .green{color:var(--moss)}
.gate .not-yet{color:var(--ink-3)}
button[disabled],.word[disabled]{opacity:.45;cursor:not-allowed}
.gate-note{margin-top:12px;font-size:13.5px;color:var(--ink-3)}

/* ---- the gauge ---- */
.gauge{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.gauge .big{font-family:var(--serif);font-size:30px;font-weight:600}
.pips{display:flex;gap:5px;flex-wrap:wrap;margin-top:10px}
.pip{width:26px;height:9px;border-radius:5px;background:var(--rule);flex:0 0 auto}
.pip.on{background:var(--accent)}

/* ---- plan and lanes ---- */
.step{display:flex;gap:12px;align-items:flex-start;min-width:0}
.step .n{
  flex:0 0 26px;height:26px;border-radius:50%;background:var(--paper-deep);
  display:grid;place-items:center;font-size:12.5px;font-weight:700;color:var(--ink-2);
}
.step .body{min-width:0;flex:1 1 auto}
.step .why{color:var(--ink-2);font-size:14px;margin-top:3px}
.evidence{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.badge{
  font-size:12px;border:1px solid var(--rule);border-radius:8px;padding:3px 9px;
  background:var(--paper-deep);color:var(--ink-2);max-width:100%;
}

/* ---- forms ---- */
label{display:block;font-size:13px;font-weight:600;color:var(--ink-2);margin-bottom:5px}
input[type=text],textarea,select{
  width:100%;max-width:100%;min-width:0;font:inherit;font-size:16px;color:var(--ink);
  background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:11px 12px;
}
textarea{min-height:110px;resize:vertical;font-family:inherit}
.field + .field{margin-top:12px}
.flash{
  border-radius:10px;padding:12px 14px;margin-bottom:14px;font-size:15px;
  background:var(--accent-soft);border:1px solid #D8CFF4;color:var(--accent-ink);
}
.flash.bad{background:#F7EEEB;border-color:#E6CFC7;color:#7A3A26}

/* ---- details fold: where the technical words live ---- */
details{margin-top:12px;border-top:1px solid var(--rule-soft);padding-top:10px}
summary{cursor:pointer;font-size:13px;font-weight:600;color:var(--ink-3);min-height:26px}
details .inner{margin-top:10px;font-family:var(--mono);font-size:12.5px;color:var(--ink-2)}
details .inner p{margin-top:5px;overflow-wrap:anywhere}

.honest{
  background:#FBF6EA;border:1px solid #E8DCC0;border-radius:10px;padding:12px 14px;
  font-size:14.5px;color:#6A5526;margin-bottom:12px;
}
.foot{margin-top:34px;padding-top:16px;border-top:1px solid var(--rule);font-size:12.5px;color:var(--ink-3)}

/* ---- desk width: the two-column shell, only when there is room ---- */
@media (min-width:900px){
  .shell{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,300px);gap:28px;padding:0 28px 80px}
  .shell > *{min-width:0}
  .rail{
    grid-column:1 / -1;margin:0 -28px 22px;padding:18px 28px 14px;
    display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;
  }
  .places{margin-top:0}
  .rows.two{grid-template-columns:repeat(2,minmax(0,1fr))}
  .aside{position:sticky;top:104px;align-self:start}
}
@media (max-width:899px){
  .aside{margin-top:22px}
}
"""
