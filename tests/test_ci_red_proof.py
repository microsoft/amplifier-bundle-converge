"""DELIBERATE DEFECT -- scratch branch only, never merged.

This file exists to prove the CI gate added in .github/workflows/ci.yml can
actually go RED, in the TEST job, with the real suite collected and executing
around it. A CI never seen red is decoration.

It carries two planted defects at once:
  * an unused import, which the pinned lint gate must catch as F401;
  * a failing assertion, which the root test job must report as a genuine
    test failure alongside the 139 real tests that pass.

Delete this file and its branch once the red run is recorded.
"""

from __future__ import annotations

import json  # noqa: intentionally unused -- the planted F401 for the lint gate


def test_ci_red_proof_root_suite_can_fail():
    assert 1 == 2, "planted failure: the root test job is really executing this suite"
