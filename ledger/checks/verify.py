#!/usr/bin/env python3
"""The ledger's own tripwires — LEDGER-FORMAT §6, made runnable.

    uv run --with pyyaml ledger/checks/verify.py        # from the repo root

Exit 0 when every tripwire holds, 1 when any fails, and it names which.

It checks, in order:

  shape        rows.yaml parses as a top-level LIST; the SYNC row is first;
               ids are unique
  §4  SYNC     every pinned contract hash matches the file on disk. A mismatch
               means a MANDATORY FULL-LEDGER RE-REVIEW, never a silent bump
  §6.3 quotes  every row's quote is a whitespace-collapsed contiguous substring
               of its contract's bytes
  §2  fields   clause ids undecorated; dispositions in PROTOCOL.md §3.3's
               vocabulary; `justification` on OPEN-PINNED / NOT-ASSERTABLE;
               `work` on GAP / VIOLATION and on nothing green;
               `assertion.kind: none` only for NOT-ASSERTABLE
  refs         every executable ref RUNS AND MEETS ITS `expect` — not merely
               resolves. This is the tripwire that matters: on 2026-09-02 the
               ledger passed a resolve-only check while 13 of its ~32 refs
               could not fail at all (an unquoted glob made `find` die and the
               test read the empty output as proof). A ref without `expect` is
               a command, not an assertion, and is failed here as one
  subjects     any out-of-repo `subject:` still hashes to its pin
  §6.1 cover   every Core clause of every contract is cited by at least one row

Deliberately NOT checked, because no machine here can: whether a row READS its
clause correctly (LEDGER-FORMAT §8), and whether an `indexed` test still
asserts what it claims. Those need the re-review the SYNC row triggers.
"""

import hashlib, pathlib, re, subprocess, sys, yaml
from collections import Counter

ROOT = pathlib.Path(".").resolve()
rows = yaml.safe_load(open("ledger/rows.yaml"))
fail = []
def chk(ok, msg):
    print(f"[{'OK  ' if ok else 'FAIL'}] {msg}")
    if not ok: fail.append(msg)

chk(isinstance(rows, list), f"parses as YAML; top-level LIST of {len(rows)} rows")
chk(rows[0]["id"] == "CVG-000" and rows[0].get("kind") == "sync", "first row is the SYNC row (CVG-000)")
ids = [r["id"] for r in rows]
chk(len(ids) == len(set(ids)), f"{len(ids)} unique ids, no duplicates")

for pin in rows[0]["pins"]:
    actual = hashlib.sha256(pathlib.Path(pin["file"]).read_bytes()).hexdigest()
    chk(actual == pin["sha256"], f"SYNC {pin['file']}  {actual}")

def collapse(s): return re.sub(r"\s+", " ", s).strip()
ctext = {f"contracts/{p.name}": collapse(p.read_text()) for p in ROOT.glob("contracts/*.md")}
q_ok = 0
for r in rows[1:]:
    c = r["contract"]
    if collapse(c["quote"]) in ctext[c["file"]]: q_ok += 1
    else: fail.append(f"{r['id']} QUOTE NOT FOUND: {collapse(c['quote'])[:70]}")
chk(q_ok == len(rows)-1, f"{q_ok}/{len(rows)-1} quotes verify byte-for-byte (whitespace-collapsed) against contract bytes")

chk(all("(" not in r["contract"]["clause"] for r in rows[1:]),
    "clause ids undecorated (no parenthetical) — LEDGER-FORMAT §2")

VOCAB = {"CONFORMS","GAP","VIOLATION","OPEN-PINNED","NOT-ASSERTABLE","EXCLUDED","DIVERGED"}
chk(all(r["disposition"] in VOCAB for r in rows[1:]), "every disposition is in the PROTOCOL §3.3 vocabulary")
red = [r for r in rows[1:] if r["disposition"] in ("GAP","VIOLATION")]
chk(all(r.get("work") for r in red), f"all {len(red)} GAP/VIOLATION rows carry a work ref")
chk(all(r.get("justification") for r in rows[1:] if r["disposition"] in ("OPEN-PINNED","NOT-ASSERTABLE")),
    "all OPEN-PINNED / NOT-ASSERTABLE rows carry a justification")
chk(all(not (r["assertion"].get("kind")=="none" and r["disposition"]!="NOT-ASSERTABLE") for r in rows[1:]),
    "assertion kind:none used only for NOT-ASSERTABLE")
chk(all(not r.get("work") for r in rows[1:] if r["disposition"] == "CONFORMS"),
    "no CONFORMS row carries a `work` ref (a tracker ref must not imply red)")

# --- THE NEW TRIPWIRE: every probe/absence ref must MEET ITS expect ---
print("\nEXECUTABLE REFS — does each one actually assert its expectation?")
n_exec = 0
for r in rows:
    a = r.get("assertion", {})
    if a.get("kind") not in ("probe", "absence"): continue
    n_exec += 1
    exp = a.get("expect")
    if not isinstance(exp, dict) or "stdout_contains" not in exp:
        fail.append(f"{r['id']} executable ref with no usable expect: — a command, not an assertion")
        print(f"  [FAIL] {r['id']:8s} no usable expect: (needs stdout_contains)"); continue
    p = subprocess.run(["bash","-c",a["ref"]], capture_output=True, text=True, timeout=180)
    okx = p.returncode == exp.get("exit", 0)
    oks = exp["stdout_contains"] in p.stdout
    print(f"  [{'OK  ' if okx and oks else 'FAIL'}] {r['id']:8s} exit={p.returncode} expect={exp.get('exit',0)}  '{exp['stdout_contains'][:52]}'")
    if not (okx and oks):
        fail.append(f"{r['id']} expect NOT met (exit={p.returncode}, stdout={p.stdout[:120]!r}, stderr={p.stderr[:120]!r})")
print(f"[{'OK  ' if not any('expect' in f for f in fail) else 'FAIL'}] {n_exec} executable refs, each meeting its declared expect")

# indexed refs resolve
missing = []
for r in rows[1:]:
    a = r["assertion"]
    if a.get("kind") != "indexed": continue
    for path in re.findall(r"[\w./-]+\.(?:py|md|yaml)", a["ref"]):
        if not pathlib.Path(path).exists(): missing.append((r["id"], path))
chk(not missing, f"every indexed ref path exists on disk ({missing or 'all resolve'})")

# proves present wherever probe truth != disposition truth (GAP row w/ passing probe)
gap_pass = [r for r in rows[1:] if r["disposition"]=="GAP" and r["assertion"].get("kind")=="probe"]
no_proves = [r["id"] for r in gap_pass if not r.get("proves") and "ADDED BY" not in str(r.get("notes",""))]
print(f"[INFO] GAP rows with a passing probe: {len(gap_pass)}; carrying `proves`: {len([r for r in gap_pass if r.get('proves')])}")

# out-of-repo subject pinned
for r in rows[1:]:
    s = r.get("subject")
    if s:
        actual = hashlib.sha256(pathlib.Path(s["path"]).read_bytes()).hexdigest()
        chk(actual == s["sha256"], f"{r['id']} out-of-repo subject pin matches: {s['path']}")

print("\nROW COUNT PER CONTRACT")
per = {}
for r in rows[1:]: per.setdefault(r["contract"]["file"], Counter())[r["disposition"]] += 1
tot = Counter()
for f in sorted(per):
    c = per[f]; tot += c
    print(f"  {f:34s} {sum(c.values()):3d} rows  " + "  ".join(f"{k}={v}" for k,v in sorted(c.items())))
print(f"  {'TOTAL (non-SYNC)':34s} {sum(tot.values()):3d} rows  " + "  ".join(f"{k}={v}" for k,v in sorted(tot.items())))
print(f"  {'TOTAL (with SYNC)':34s} {len(rows):3d}")

print("\nCLAUSE COVERAGE (every Core clause cited by >=1 row)")
for p in sorted(ROOT.glob("contracts/*.md")):
    core = p.read_text().split("## Core (the teeth)")[1].split("\n## ")[0]
    n = len(re.findall(r"^\d+\.\s", core, re.M))
    cited = {r["contract"]["clause"] for r in rows[1:] if r["contract"]["file"] == f"contracts/{p.name}"}
    miss = [f"Core {i}" for i in range(1, n+1) if f"Core {i}" not in cited]
    print(f"  {p.name:24s} {n:2d} Core clauses, cited {n-len(miss)}/{n}" + (f"  MISSING {miss}" if miss else "  OK"))
    if miss: fail.append(f"{p.name} missing {miss}")

print()
if fail:
    print("FAILURES:"); [print("  -", f) for f in fail]; sys.exit(1)
print("ALL LEDGER SELF-CHECKS PASS")
