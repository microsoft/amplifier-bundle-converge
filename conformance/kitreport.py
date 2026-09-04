"""The report shape every Converge conformance kit prints, in one place.

`conformance/README.md` promises that every kit behaves the same way — a JSON
report on stdout, a human summary on stderr, exit 0 unless a rule FAILs, and
only three statuses. The three experience kits get that from here rather than
each carrying its own copy, so the promise cannot drift kit by kit.

Three statuses, and only three:

``PASS``
    The kit checked this and the promise is kept.
``FAIL``
    The kit checked this and the promise is broken. The detail names what it
    read and what it expected.
``SKIP``
    The kit **could not check this**, and says why in a ``reason`` field. A
    SKIP is never a soft pass.
"""

from __future__ import annotations

import argparse
import json
import sys

from appsnapshot import TargetError, resolve_target

__all__ = ["Kit", "run_cli"]


class Kit:
    """One kit's rule table, and the results it emits."""

    def __init__(self, name: str, contract: str, rules, unfixturable=None):
        #: rules: [(rule_id, core_clause:int, short_id, one-line promise), …]
        self.name = name
        self.contract = contract
        self.rules = list(rules)
        self.unfixturable = dict(unfixturable or {})
        seen = [r[0] for r in self.rules]
        if len(seen) != len(set(seen)):
            raise ValueError(f"{name}: duplicate rule id in the table")

    def rule(self, rid):
        for r in self.rules:
            if r[0] == rid:
                return r
        raise KeyError(f"{self.name}: no rule {rid!r} in the table")

    def result(self, rid, status, detail, **extra):
        _, clause, short, promise = self.rule(rid)
        out = {"rule": rid, "clause": clause, "id": short, "name": promise,
               "status": status, "detail": detail}
        if status == "SKIP":
            out["reason"] = detail
        out.update(extra)
        return out

    def ok(self, rid, detail, **extra):
        return self.result(rid, "PASS", detail, **extra)

    def bad(self, rid, detail, **extra):
        return self.result(rid, "FAIL", detail, **extra)

    def skip(self, rid, reason=None, **extra):
        return self.result(rid, "SKIP", reason or self.unfixturable[rid], **extra)

    def report(self, snapshot, results, **extra):
        summary = {
            "pass": sum(r["status"] == "PASS" for r in results),
            "fail": sum(r["status"] == "FAIL" for r in results),
            "skip": sum(r["status"] == "SKIP" for r in results),
        }
        out = {
            "kit": self.name,
            "contract": self.contract,
            "target": snapshot.base,
            "target_kind": snapshot.kind,
            "manager": snapshot.manager_id(),
            "routes_read": len(snapshot.order),
            "check": ("static — read from what the app served (shell, API payloads, "
                      "client assets, its own route table); no browser is launched"),
            "results": results,
            "summary": summary,
            "verdict": "FAIL" if summary["fail"] else "PASS",
        }
        out.update(extra)
        return out


def print_human_summary(report: dict) -> None:
    write = sys.stderr.write
    write(f"\n{report['kit']} conformance — {report['target']} "
          f"({report['target_kind']}, {report['routes_read']} route(s))\n")
    write(f"asserts: {report['contract']} — {report['check']}\n")
    write("-" * 78 + "\n")
    for result in report["results"]:
        write(f"  [{result['status']:4}] {result['rule']:3} {result['id']}: "
              f"{result['detail']}\n")
    write("-" * 78 + "\n")
    s = report["summary"]
    write(f"  VERDICT: {report['verdict']}  "
          f"(pass={s['pass']} fail={s['fail']} skip={s['skip']})\n\n")


def run_cli(prog: str, description: str, run_conformance, argv=None) -> int:
    """The command line every experience kit shares."""
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument("target",
                        help="the running app (http://127.0.0.1:8788) or a directory "
                             "written by --capture")
    parser.add_argument("--cookie", default="",
                        help="the app's signed session cookie; $CONVERGE_APP_COOKIE is "
                             "used when this is absent")
    parser.add_argument("--capture", default="", metavar="DIR",
                        help="write every route read to DIR (with a manifest naming the "
                             "route each file came from), so it can be judged again later")
    parser.add_argument("--json-only", action="store_true",
                        help="suppress the human summary on stderr")
    args = parser.parse_args(argv)

    try:
        snapshot = resolve_target(args.target, args.cookie)
        if args.capture:
            snapshot.capture(args.capture)
        report = run_conformance(snapshot)
    except TargetError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 3

    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    if not args.json_only:
        print_human_summary(report)
    return 1 if report["verdict"] == "FAIL" else 0
