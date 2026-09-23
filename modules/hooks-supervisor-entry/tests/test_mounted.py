import asyncio
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.asyncio
from amplifier_core import ToolResult

from amplifier_module_hooks_supervisor_entry.mounted import mounted_reader


async def test_explicit_tool_receives_only_public_read_and_exact_structured_payload():
    calls = []
    payload = {"entries": [], "count": 0}
    async def execute(args):
        calls.append(args)
        return ToolResult(success=True, output={"mcp_tool": "converge_operations", "content": "truncated",
            "content_truncated": True, "structured_content": {"result": payload}})
    tool = SimpleNamespace(execute=execute)
    c = SimpleNamespace(get=lambda key: {"configured": tool})
    result = await mounted_reader(c, "configured")({"section": "projects", "limit": 3},
                                                  deadline=asyncio.get_running_loop().time()+1)
    assert result is payload or result == payload
    assert calls == [{"action": "read", "arguments": {"section": "projects", "limit": 3}}]


@pytest.mark.parametrize("output", [{"content": '{"entries":[]}'},
    {"mcp_tool": "other", "structured_content": {"result": {}}},
    {"mcp_tool": "converge_operations", "structured_content": None}])
async def test_other_wrappers_and_text_previews_are_not_records(output):
    async def execute(args):return ToolResult(success=True, output=output)
    c = SimpleNamespace(get=lambda key: {"configured": SimpleNamespace(execute=execute)})
    with pytest.raises(ValueError):
        await mounted_reader(c, "configured")({}, deadline=asyncio.get_running_loop().time()+1)


async def test_no_automatic_tool_selection_or_retry():
    c = SimpleNamespace(get=lambda key: {})
    assert mounted_reader(c, None) is None
    with pytest.raises(ValueError):
        await mounted_reader(c, "missing")({}, deadline=asyncio.get_running_loop().time()+1)
