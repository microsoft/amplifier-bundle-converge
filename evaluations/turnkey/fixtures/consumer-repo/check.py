#!/usr/bin/env python3
"""Component and cross-boundary checks for the producer/consumer fixture."""

from __future__ import annotations

import argparse
import json

import consumer
import producer


def component_report() -> dict:
    results = [
        {"component": "producer", "status": "PASS" if producer.component_check() else "FAIL"},
        {"component": "consumer", "status": "PASS" if consumer.component_check() else "FAIL"},
    ]
    return {
        "kind": "component",
        "results": results,
        "verdict": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL",
    }


def consumer_report() -> dict:
    expected_context = "trial-context"
    record = producer.publish(expected_context)
    association_ok = record.get("context_id") == expected_context
    value = consumer.consume(record)
    return {
        "kind": "consumer",
        "expected_context": expected_context,
        "received_context": record.get("context_id"),
        "received_value": value,
        "verdict": "PASS" if association_ok else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()
    report = component_report() if args.component else consumer_report()
    if args.json_only:
        print(json.dumps(report, sort_keys=True))
    else:
        print(f"{report['kind']} check: {report['verdict']}")
        if report["kind"] == "consumer":
            print(f"context: expected {report['expected_context']!r}, "
                  f"received {report['received_context']!r}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())