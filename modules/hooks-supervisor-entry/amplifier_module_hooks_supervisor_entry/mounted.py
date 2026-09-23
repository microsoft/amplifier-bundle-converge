"""Explicitly configured public tool-mcp binding; never guess a server/tool."""
from __future__ import annotations

import asyncio


def mounted_reader(coordinator, name):
    if not isinstance(name, str) or not name or len(name) > 240:
        return None

    async def read(arguments, *, deadline):
        tool = coordinator.get("tools").get(name)
        if tool is None:
            raise ValueError("Configured public tool is unavailable.")
        response = await asyncio.wait_for(tool.execute({"action": "read", "arguments": dict(arguments)}),
                                          max(0, deadline - asyncio.get_running_loop().time()))
        output = response.output
        # Qualified tool-mcp wrapper shape. Its display text can be truncated;
        # the structured result remains the exact domain payload. Never parse
        # a text preview or a different wrapper as an equivalent record.
        if not response.success or not isinstance(output, dict) or output.get("mcp_tool") != "converge_operations":
            raise ValueError("Configured public tool did not return an Operations receipt.")
        structured = output.get("structured_content")
        if not isinstance(structured, dict) or not isinstance(structured.get("result"), dict):
            raise ValueError("Operations structured result is unavailable.")
        return structured["result"]

    return read
