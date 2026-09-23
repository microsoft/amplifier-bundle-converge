"""Current reports come from this overview, not remembered model history."""
import copy
import json
import pytest
from test_observation import Public, row, run
from amplifier_module_hooks_supervisor_entry.observe import MAX_CONTEXT_BYTES, encoded
from amplifier_module_hooks_supervisor_entry import mount
from test_mount import session
from amplifier_module_hooks_supervisor_entry.observe import CAPABILITY

pytestmark = pytest.mark.asyncio

def current(public, text="Integrated example is locally open", ordering="recorded_time", count=1):
    public.manager.update(generation="generation-a", status="idle", owner_present=True)
    entries = []
    for i in range(count):
        entry = row("run", f"run-{i}", status="reported", manager_relation="current", ended_at=100)
        entry["report"] = {"excerpt":text, "complete":True,
            "read":{**entry["read"], "arguments":{**entry["read"]["arguments"], "field":"result"}}}
        entries.append(entry)
    guidance = {"records_available":True, "manager_observation":{**public.manager,"identity_complete":True},
        "latest_reports":{"entries":entries,"count":count,"included":count,"omitted":0,
            "unconfirmed_count":0,"ordering":ordering,"read":{"capability":"operations","action":"read",
            "arguments":{"project_id":"project-a","list_kind":"run","limit":3}}}}
    def enrich(args,result):
        if args.get("section")=="overview":
            result["current_summary"]="Manager idle; newest recorded report available"
            result["product_overview"]["guidance"]=copy.deepcopy(guidance)
        return result
    public.mutate=enrich
    return guidance

async def test_latest_report_refreshes_each_observation_without_more_reads():
    p=Public();current(p,"Earlier verification still running")
    first=await run(p);calls=len(p.calls)
    current(p,"Integrated example is locally open")
    second=await run(p)
    assert len(p.calls)==2*calls==6
    value=second["current"]
    assert value["source"]=="operations.overview" and value["manager_generation"]=="generation-a"
    assert value["latest_reports"]["entries"][0]["report"]["excerpt"]=="Integrated example is locally open"
    assert "Earlier verification" not in encoded(second)
    assert value["latest_reports"]["entries"][0]["report"]["read"]["arguments"]["field"]=="result"
    assert "ready" not in second and first["current"]!=value

@pytest.mark.parametrize("field,value",[("generation","old"),("native_session_id","other"),("id","other"),("revision",2)])
async def test_mixed_owner_projection_is_never_current(field,value):
    p=Public();g=current(p);g["manager_observation"][field]=value
    assert (await run(p))["status"]=="read_incomplete"

async def test_tied_missing_and_omitted_reports_remain_explicit():
    p=Public();g=current(p,ordering="ambiguous",count=2)
    result=(await run(p))["current"]["latest_reports"]
    assert result["ordering"]=="ambiguous" and result["included"]==2
    g["latest_reports"].update(entries=[],included=0,omitted=2,ordering="unknown",unconfirmed_count=1)
    result=(await run(p))["current"]["latest_reports"]
    assert result["count"]==2 and result["omitted"]==2 and result["ordering"]=="unknown"
    g["records_available"]=False
    assert (await run(p))["current"]=={"status":"unavailable"}

async def test_foreign_result_handle_refuses_and_no_new_actions():
    p=Public();g=current(p)
    g["latest_reports"]["entries"][0]["report"]["read"]["arguments"]["project_id"]="foreign"
    assert (await run(p))["status"]=="read_incomplete" and len(p.calls)==3

async def test_unicode_excerpts_budget_and_omission_preserve_selection():
    p=Public();p.selected();current(p,"😀"*10000,count=3,ordering="ambiguous")
    result=await run(p)
    assert result["status"]=="matched" and result["review"]["status"]=="selected"
    assert len(encoded(result).encode())<MAX_CONTEXT_BYTES-1000
    bucket=result["current"]["latest_reports"]
    assert bucket["count"]==3 and bucket["included"]+bucket["omitted"]==3
    assert all(not r["report"]["complete"] and len(r["report"]["excerpt"].encode())<=600 for r in bucket["entries"])

async def test_five_second_mount_injects_asof_source_before_request_and_refreshes():
    c=session().coordinator;p=Public();current(p,"New current report")
    c.register_capability("session.working_dir","/work/example");c.register_capability(CAPABILITY,p)
    unregister=await mount(c,{"enabled":True,"role":"supervisor","deadline_seconds":5})
    result=await c.hooks.emit("prompt:submit",{})
    data=json.loads(result.context_injection.split("\n",1)[1])
    assert data["observed_at"] and data["facts"]["current"]["source"]=="operations.overview"
    assert "New current report" in result.context_injection and result.ephemeral
    current(p,"Later report")
    result=await c.hooks.emit("prompt:submit",{})
    assert "Later report" in result.context_injection and "New current report" not in result.context_injection
    unregister()
