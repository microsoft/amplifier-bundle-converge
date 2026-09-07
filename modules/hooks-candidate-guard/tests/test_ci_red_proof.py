"""DELIBERATE DEFECT -- scratch branch only, never merged.

Proves the per-module test job collects and executes the module's own suite,
rather than passing because it found nothing to run.
"""

from __future__ import annotations


def test_ci_red_proof_module_suite_can_fail():
    assert 1 == 2, "planted failure: the module test job is really executing this suite"
