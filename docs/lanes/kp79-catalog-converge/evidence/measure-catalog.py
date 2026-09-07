#!/usr/bin/env python3
"""Per-bundle byte attribution of a rendered delegate agent catalog.

Usage: measure-catalog.py BEFORE.txt AFTER.txt
Prints the per-bundle slice table plus the control (every bundle other than
`converge` must show delta 0).
"""
import re
import sys


def slices(path: str) -> dict[str, int]:
    """Bytes each bundle's agent entries occupy in the rendered catalog."""
    text = open(path, encoding="utf-8").read()
    out: dict[str, int] = {}
    cur: str | None = None
    for line in text.splitlines(keepends=True):
        m = re.match(r"^  - ([a-z0-9_-]+):([a-zA-Z0-9_-]+): ", line)
        if m:
            cur = m.group(1)
        elif re.match(r"^  - ", line):
            cur = None
        if cur:
            out[cur] = out.get(cur, 0) + len(line.encode())
    return out


def main() -> None:
    before_path, after_path = sys.argv[1], sys.argv[2]
    b, a = slices(before_path), slices(after_path)
    wb = len(open(before_path, "rb").read())
    wa = len(open(after_path, "rb").read())
    print(f"BEFORE whole delegate tool description: {wb:,} B")
    print(f"AFTER  whole delegate tool description: {wa:,} B")
    print(f"DELTA: {wa - wb:+,} B\n")
    print("PER-BUNDLE SLICE OF THE RENDERED AGENT CATALOG (bytes)")
    print(f"{'bundle':<28}{'before':>9}{'after':>9}{'delta':>9}")
    moved = []
    for k in sorted(set(b) | set(a)):
        bb, aa = b.get(k, 0), a.get(k, 0)
        if bb != aa:
            moved.append(k)
        print(f"{k:<28}{bb:>9,}{aa:>9,}{aa - bb:>+9,}")
    print(f"\nCONTROL: bundles with non-zero delta = {moved}  (expected exactly ['converge'])")
    print(f"Bundles with delta 0: {len(set(b) | set(a)) - len(moved)} of {len(set(b) | set(a))}")


if __name__ == "__main__":
    main()
