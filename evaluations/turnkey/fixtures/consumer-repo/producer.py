"""The producer side of the deliberately tiny consumer fixture."""


def publish(context_id: str) -> dict[str, object]:
    """Publish a usable payload, but (deliberately) lose its association."""
    return {"kind": "reading", "value": 21, "context_id": "unassociated"}


def component_check() -> bool:
    record = publish("component-context")
    return record["kind"] == "reading" and record["value"] == 21