#!/usr/bin/env bash
# Run validate-agents v1.7.0's OWN deterministic validator steps (agent-discovery,
# structural-validation, quality-classification) directly against a repo.
#
# WHY THIS EXISTS: the recipe itself CRASHES on this repo (and on any repo whose
# agent descriptions are YAML folded/literal scalars). Its quality-classification
# step does `json.loads('''{{structural_results}}''')` -- interpolating a JSON
# payload into a PYTHON TRIPLE-QUOTED LITERAL. The description's trailing newline
# is JSON-escaped as the two characters \n; Python's literal parser turns that back
# into a REAL newline, which is illegal inside a JSON string, so json.loads dies with
# `Expecting ',' delimiter`. Pre-existing: it fails identically on origin/main.
#
# This harness runs the identical step scripts, passing each payload through a FILE
# instead of a string literal. Nothing else is changed. No LLM call, $0.
set -euo pipefail
REPO="${1:?usage: run-validate-agents.sh <repo-path>}"
RECIPE="${VALIDATE_AGENTS_RECIPE:-$HOME/.amplifier/cache/amplifier-foundation-c909465861f9d6ce/recipes/validate-agents.yaml}"
WORK="$(mktemp -d)"
python3 - "$RECIPE" "$WORK" <<'PY'
import sys, yaml, pathlib
recipe, work = sys.argv[1], pathlib.Path(sys.argv[2])
steps = {s["id"]: s["command"] for s in yaml.safe_load(pathlib.Path(recipe).read_text())["steps"] if "command" in s}
for sid in ("agent-discovery", "structural-validation", "quality-classification"):
    (work / f"{sid}.sh").write_text(steps[sid])
PY
sed -i "s|{{repo_path}}|$REPO|g" "$WORK/agent-discovery.sh"
bash "$WORK/agent-discovery.sh" > "$WORK/discovery.json"
python3 - "$WORK" <<'PY'
import sys, pathlib
w = pathlib.Path(sys.argv[1])
sv = (w / "structural-validation.sh").read_text().replace(
    "json.loads('''{{discovery_results}}''')",
    'json.loads(open(os.environ["VA_DISCOVERY"]).read())')
(w / "structural-validation.sh").write_text(sv)
qc = (w / "quality-classification.sh").read_text().replace(
    "json.loads('''{{structural_results}}''')",
    'json.loads(open(os.environ["VA_STRUCTURAL"]).read())').replace(
    "import json", "import json, os", 1)
(w / "quality-classification.sh").write_text(qc)
PY
sed -i "s|{{repo_path}}|$REPO|g" "$WORK/structural-validation.sh"
VA_DISCOVERY="$WORK/discovery.json" bash "$WORK/structural-validation.sh" > "$WORK/structural.json"
VA_STRUCTURAL="$WORK/structural.json" bash "$WORK/quality-classification.sh" > "$WORK/quality.json"
python3 - "$WORK" <<'PY'
import sys, json, pathlib
w = pathlib.Path(sys.argv[1])
d = json.loads((w / "discovery.json").read_text())
s = json.loads((w / "structural.json").read_text())
q = json.loads((w / "quality.json").read_text())
print("=== validate-agents v1.7.0 (own steps, run directly) ===")
print("DISCOVERY: candidates_scanned=%s agents_found=%s non_agents=%s"
      % (d.get("candidates_scanned"), d.get("total_count"), d.get("non_agent_count")))
for n in d.get("non_agents_found", []):
    print("   non-agent:", n)
print("AGENTS:", ", ".join(sorted(a["name"] if isinstance(a, dict) else str(a) for a in d.get("agents_found", []))))
errs = [f for f in s.get("findings", []) if f.get("severity") == "ERROR"]
warns = [f for f in s.get("findings", []) if f.get("severity") == "WARNING"]
print("STRUCTURAL: errors=%d warnings=%d" % (len(errs), len(warns)))
for f in errs + warns:
    print("   %s %s: %s" % (f.get("severity"), f.get("agent"), f.get("code") or f.get("message")))
print("QUALITY VERDICT:", json.dumps({k: v for k, v in q.items() if k != "agents"}, indent=2)[:1200])
for a in q.get("agents", []):
    print("   %-22s %-10s desc=%s tok=%s examples=%s commentary=%s tools=%s :: %s"
          % (a.get("name"), a.get("quality"), a.get("description_length"),
             a.get("description_tokens"), a.get("has_examples"), a.get("commentary_count"),
             a.get("has_explicit_tools"), a.get("reason")))
PY
echo "(work dir: $WORK)"
