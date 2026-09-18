"""The consumer side of the deliberately tiny consumer fixture."""


def consume(record: dict[str, object]) -> int:
    if record["kind"] != "reading":
        raise ValueError("consumer accepts only readings")
    return int(record["value"]) * 2


def component_check() -> bool:
    return consume({"kind": "reading", "value": 21, "context_id": "component-context"}) == 42