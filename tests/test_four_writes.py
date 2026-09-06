"""Surface.v1 clause 3: exactly four writes, each a manager-session operation.

The number is the promise, and it used to be asserted three ways: the registry
holds four entries, the page exposed four write routes and no more, and every
form on every page posted to one of them. The page was retired on 2026-09-06 on
the steward's word, so the two assertions that read its routes went with it.
The registry stays, and it is where the cap is actually enforced — `writing/`
raises at import time if a fifth is added without amending the contract first.
"""

from __future__ import annotations

from amplifier_converge.writing import EXPECTED_WRITE_COUNT, WRITES

EXPECTED = {
    "answer-with-a-word",
    "signal-priority",
    "drop-feedback",
    "steer",
}


def test_registry_holds_exactly_four():
    assert len(WRITES) == EXPECTED_WRITE_COUNT == 4
    assert {write.name for write in WRITES} == EXPECTED


def test_every_write_names_a_manager_operation():
    for write in WRITES:
        assert write.manager_operation.strip(), f"{write.name} names no manager operation"
        assert write.lands_in.strip(), f"{write.name} does not say where it lands"
