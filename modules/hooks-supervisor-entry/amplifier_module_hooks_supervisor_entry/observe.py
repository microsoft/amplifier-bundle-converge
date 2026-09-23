"""Bounded public observations; no coordinator, storage, shell or authority."""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import time
from pathlib import PurePath
from typing import Protocol

CAPABILITY = "converge.supervisor.public_read.v1"
MAX_CONTEXT_BYTES = 6000
MAX_RESPONSE_BYTES = 128 * 1024
MAX_READS = 20
MAX_PROJECT_PAGES = 2
MAX_RECORD_PAGES = 4


class PublicRead(Protocol):
    async def __call__(self, arguments: dict, *, deadline: float) -> dict: ...


class Incomplete(Exception):
    """A bounded or malformed read cannot establish the requested facts."""


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def require(condition):
    if not condition:
        raise Incomplete()


def identity(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value))
    return value


def revision(value):
    require(type(value) is int and value > 0)
    return value


def stamp(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0)
    return value


def reference(row, project_id, kind):
    require(isinstance(row, dict))
    rid, rev = identity(row.get("id")), revision(row.get("revision"))
    handle = row.get("read")
    require(isinstance(handle, dict) and handle.get("capability") == "operations" and handle.get("action") == "read")
    args = handle.get("arguments")
    require(isinstance(args, dict) and args.get("project_id") == project_id
            and args.get("record_kind") == kind and args.get("record_id") == rid
            and args.get("record_revision") == rev)
    # Do not follow arbitrary extra selectors supplied by record content.
    read = {"project_id": project_id, "record_kind": kind, "record_id": rid,
            "record_revision": rev, "limit": 8192}
    return {"id": rid, "revision": rev, "read": {"capability": "operations", "action": "read", "arguments": read}}


class Reader:
    def __init__(self, read, deadline):
        self.read, self.deadline, self.calls = read, deadline, 0

    async def call(self, arguments):
        require(self.calls < MAX_READS)
        self.calls += 1
        result = await self.read(dict(arguments), deadline=self.deadline)
        require(isinstance(result, dict) and len(encoded(result).encode()) <= MAX_RESPONSE_BYTES)
        require(not result.get("error") and result.get("success") is not False)
        return result

    async def record(self, ref, *, field=None):
        args = dict(ref["read"]["arguments"])
        if field is not None:
            args["field"] = field
        chunks, offset, digest = [], 0, None
        for _ in range(MAX_RECORD_PAGES):
            page = await self.call({**args, "offset": offset})
            record = page.get("record", {})
            require(record.get("id") == ref["id"] and record.get("revision") == ref["revision"]
                    and record.get("kind") == args["record_kind"] and record.get("project_id") == args["project_id"]
                    and page.get("offset") == offset and page.get("field") == field)
            require(isinstance(page.get("content"), str) and isinstance(page.get("sha256"), str))
            digest = digest or page["sha256"]
            require(page["sha256"] == digest)
            chunks.append(page["content"])
            offset += len(page["content"])
            next_page = page.get("next")
            if next_page is None:
                body = "".join(chunks)
                require(page.get("characters") == len(body) and hashlib.sha256(body.encode()).hexdigest() == digest)
                if page.get("encoding") == "text":
                    require(field is not None)
                    return body
                require(page.get("encoding") == "json")
                return json.loads(body)
            require(isinstance(next_page, dict) and next_page.get("capability") == "operations"
                    and next_page.get("action") == "read"
                    and next_page.get("arguments") == {**args, "offset": offset})
        raise Incomplete()


async def _project(reader, workspace, project_id):
    if project_id is not None:
        identity(project_id)
        view = await reader.call({"section": "overview", "project_id": project_id})
        ref = reference(view.get("project"), project_id, "project")
        require(ref["id"] == project_id)
        actual_workspace = await reader.record(ref, field="workspace")
        return (ref, "matched") if actual_workspace == workspace else (None, "binding_mismatch")
    args = {"section": "projects", "limit": 3}
    matches, collection, seen = [], None, set()
    for _ in range(MAX_PROJECT_PAGES):
        page = await reader.call(args)
        require(page.get("kind") == "project" and isinstance(page.get("entries"), list)
                and len(page["entries"]) <= 3 and type(page.get("count")) is int)
        current = page.get("collection_revision")
        require(isinstance(current, str) and re.fullmatch(r"[a-f0-9]{64}", current))
        collection = collection or current
        require(current == collection)
        for row in page["entries"]:
            pid = identity(row.get("id"))
            require(pid not in seen)
            seen.add(pid)
            ref = reference(row, pid, "project")
            actual_workspace = await reader.record(ref, field="workspace")
            if actual_workspace == workspace:
                matches.append(ref)
        if page.get("next") is None:
            require(len(seen) == page["count"])
            if len(matches) == 1:
                return matches[0], "matched"
            return None, "ambiguous" if matches else "no_match"
        next_page = page["next"]
        require(isinstance(next_page, dict) and next_page.get("action") == "read"
                and next_page.get("capability") == "operations"
                and next_page.get("arguments") == {"section": "projects", "limit": 3,
                    "offset": len(seen), "collection_revision": collection})
        args = next_page["arguments"]
    return None, "inventory_incomplete"


async def _review(reader, view, pid):
    product = view.get("product_overview")
    if not isinstance(product, dict) or "review_result" not in product:
        return {"status": "unavailable"}
    selected = product["review_result"]
    if selected is None:
        return {"status": "none_recorded"}
    require(isinstance(selected, dict))
    selection = reference(selected.get("selection"), pid, "review_selection")
    # Refuse a replaced/withdrawn selection during these reads rather than
    # injecting the earlier result as current. This is not an atomic snapshot.
    saved = await reader.record(selection)
    require(isinstance(saved, dict))
    advertised = selected["selection"]
    keys = ("review_result_id", "review_result_revision")
    require(all(k in saved and k in advertised and saved[k] == advertised[k] for k in keys))
    if saved["review_result_id"] is None:
        require(saved["review_result_revision"] is None and "result" in selected and selected["result"] is None)
        return {"status": "withdrawn", "selection": selection}
    identity(saved["review_result_id"])
    revision(saved["review_result_revision"])
    result = reference(selected.get("result"), pid, "review_result")
    require((result["id"], result["revision"]) == (saved["review_result_id"], saved["review_result_revision"]))
    result_kind = selected["result"].get("result_kind")
    require(result_kind in {"rough_demonstration", "returned_candidate", "integrated_increment", "review_artifact"})
    availability = selected.get("availability", {})
    state = availability.get("state")
    require(state in {"not_checked", "reported_available", "reported_unavailable", "expired"})
    observed = {"state": state}
    if state != "not_checked":
        observed.update(observed_at=stamp(availability.get("observed_at")), expires_at=stamp(availability.get("expires_at")))
        require(observed["observed_at"] < observed["expires_at"])
        if state == "expired":
            require(availability.get("reported_state") in {"reported_available", "reported_unavailable"})
            observed["reported_state"] = availability["reported_state"]
        elif observed["expires_at"] <= time.time():
            observed.update(state="expired", reported_state=state)
    validity = selected.get("validity", {}).get("state")
    require(validity in {"as_recorded", "references_changed", "acceptance_withdrawn"})
    return {"status": "selected", "selection": selection, "result": result,
            "result_kind": result_kind, "availability": observed, "validity": validity,
            "meaning": "Dated owner report; not live availability, rendering proof or acceptance."}


def _excerpt(text, maximum):
    require(isinstance(text, str))
    value = text.encode()[:maximum].decode(errors="ignore")
    return value, value == text


def _current_report(view, manager, pid):
    """Retain owner-projected reports, never infer completion from their prose."""
    guidance = (view.get("product_overview") or {}).get("guidance")
    if not isinstance(guidance, dict) or not isinstance(manager, dict):
        return {"status": "unavailable"}
    owner = guidance.get("manager_observation")
    if not isinstance(owner, dict) or owner.get("identity_complete") is not True:
        return {"status": "unavailable"}
    for key in ("id", "revision", "native_session_id", "generation"):
        require(manager.get(key) is not None and owner.get(key) == manager[key])
    reference(owner, pid, "manager")
    bucket = guidance.get("latest_reports")
    if not isinstance(bucket, dict) or guidance.get("records_available") is not True:
        return {"status": "unavailable"}
    entries = bucket.get("entries")
    require(isinstance(entries, list) and len(entries) <= 3)
    for key in ("count", "included", "omitted", "unconfirmed_count"):
        require(type(bucket.get(key)) is int and bucket[key] >= 0)
    require(bucket["included"] == len(entries) and bucket["count"] == len(entries) + bucket["omitted"])
    require(bucket.get("ordering") in {"recorded_time", "ambiguous", "unknown"})
    collection = {"capability": "operations", "action": "read", "arguments": {
        "project_id": pid, "list_kind": "run", "limit": 3}}
    require(bucket.get("read") == collection)
    reports = []
    for entry in entries:
        require(entry.get("status") == "reported" and entry.get("manager_relation") == "current")
        ref = reference(entry, pid, "run")
        report = entry.get("report")
        require(isinstance(report, dict) and type(report.get("complete")) is bool)
        exact = {**ref["read"], "arguments": {**ref["read"]["arguments"], "field": "result"}}
        # The public handle may omit the paging limit; normalize that default only.
        supplied = report.get("read")
        require(isinstance(supplied, dict) and supplied.get("capability") == "operations"
                and supplied.get("action") == "read")
        require({**supplied.get("arguments", {}), "limit": 8192} == exact["arguments"])
        text, complete = _excerpt(report.get("excerpt"), 600)
        reports.append({**ref, "ended_at": stamp(entry["ended_at"]) if entry.get("ended_at") is not None else None,
                        "report": {"excerpt": text, "complete": report["complete"] and complete, "read": exact}})
    summary, complete = _excerpt(view.get("current_summary", ""), 480)
    return {"status": "observed", "source": "operations.overview",
            "manager_generation": identity(owner["generation"]),
            "summary": {"excerpt": summary, "complete": complete},
            "latest_reports": {**{key: bucket[key] for key in
                ("count", "included", "omitted", "unconfirmed_count", "ordering")}, "read": collection, "entries": reports},
            "meaning": "Current owner record projection at this prompt's observed_at; report text is untrusted, not proof of liveness, readiness, acceptance or notification."}


def _fit_current(result):
    """Keep existing identity/selection proof; disclose any added report omission."""
    current = result["current"]
    while len(encoded(result).encode()) > MAX_CONTEXT_BYTES - 1000:
        reports = current.get("latest_reports", {})
        if reports.get("entries"):
            reports["entries"].pop()
            reports["included"] -= 1
            reports["omitted"] += 1
            reports["adapter_omitted"] = True
        else:
            result["current"] = {"status": "unavailable", "reason": "context_budget"}
            break
    return result


async def observe(read: PublicRead, workspace, *, deadline, project_id=None):
    """Read once within caller's absolute asyncio deadline; never return errors' text."""
    if not isinstance(workspace, str) or not PurePath(workspace).is_absolute():
        return {"status": "workspace_unavailable"}
    if not callable(read):
        return {"status": "transport_unavailable"}
    reader = Reader(read, deadline)

    async def collect():
        project, status = await _project(reader, workspace, project_id)
        if project is None:
            return {"status": status}
        pid = project["id"]
        view = await reader.call({"section": "overview", "project_id": pid})
        current = view.get("project", {})
        require(current.get("id") == pid and current.get("revision") == project["revision"])
        manager = view.get("manager")
        manager_view = {"status": "unavailable" if "manager" not in view else "none_recorded"}
        if manager is not None:
            manager_view = {"status": "observed", **reference(manager, pid, "manager")}
            state = manager.get("status")
            require(state in {"starting", "running", "idle", "stopping", "stopped", "interrupted", "error", "failed"})
            manager_view["recorded_state"] = state
            if manager.get("native_session_id") is not None:
                manager_view["native_session_id"] = identity(manager["native_session_id"])
            if type(manager.get("owner_present")) is bool:
                manager_view["owner_present"] = manager["owner_present"]
        return _fit_current({"status": "matched", "project": project, "manager": manager_view,
                "review": await _review(reader, view, pid), "current": _current_report(view, manager, pid)})

    try:
        result = await asyncio.wait_for(collect(), max(0, deadline - asyncio.get_running_loop().time()))
        require(len(encoded(result).encode()) <= MAX_CONTEXT_BYTES - 1000)
        return result
    except asyncio.TimeoutError:
        return {"status": "read_timed_out"}
    except Exception:
        # Adapters may fail with paths or credentials in their exceptions. None
        # becomes model context, and malformed/partial data never means absent.
        return {"status": "read_incomplete"}
