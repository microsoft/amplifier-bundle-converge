# Optional supervisor entry context

This module supplies a small, dated public project observation before a root
supervisor's first tool choice on each prompt. It addresses operation Core 3/7
and composition Core 6: the customer should not have to find the manager, and
observed records must not become invented readiness or authority.

It is **opt-in** through `behaviors/supervisor-entry.yaml`. Existing root,
collaborative, CLI modes, supervisor/manager instructions and tools are unchanged.
Include it only with a supervising conversation and a public-read adapter.
Loading it does not create a project, admit instructions, reconnect a manager,
publish a result, grant permission, or make unrelated chat Converge work.

## Public-read adapter

Register the coordinator capability `converge.supervisor.public_read.v1`:

```python
async def read(arguments: dict, *, deadline: float) -> dict:
    # Execute public Operations action="read", reconcile its exact receipt,
    # then return the exact domain result. No request_id or mutation is sent.
    ...
```

`deadline` is absolute `asyncio.get_running_loop().time()`, shared by every
discovery, transport, receipt and page read in this observation. Raise on missing
transport, stale scope, incomplete receipts or errors. The observer never copies
exception text into context and never falls back to shell, history or private
storage. An adapter must not replay uncertain mutations. The capability is
resolved at prompt time so adapters can mount after this hook.

For a configured portable `tool-mcp` session, `mounted_tool` may name its exact
mounted Operations tool (for example `mcp_converge_converge_operations`). When no
capability is registered, the hook uses that explicit tool's `execute` interface,
always with `{action: "read", arguments: ...}`. It accepts only the qualified
MCP wrapper's `structured_content.result`, never a truncated text preview. It
does not discover or launch servers; normal MCP configuration owns the connection.
Missing/failed capabilities are not silently retried through the fallback.

The portable library `observe.py` has no Core or host import. Its only selectors
are project inventory, a project overview, and revision-bound `project.workspace`
or complete `review_selection` record pages. Exact manager/result read handles
remain available to the supervisor. The observation also retains bounded current owner report excerpts as explicitly
untrusted record data, with exact result-field read handles and report ordering,
counts and omissions. No environment or error text is injected.

## Bounds and scope

The total deadline defaults to two seconds, configurable with `deadline_seconds`
up to five. Each observation permits at most 20 reads, two inventory pages of
three projects, four pages per record, 128 KiB per domain response and 6,000 bytes
of context. A cold transport may exhaust this allowance; it reports uncertainty,
not absence. These are safety bounds, not measured live performance promises.

An optional `project_id` selects an already established binding. It is checked
against the current `session.working_dir`; mismatch never silently retargets.
Otherwise only a complete inventory and exactly one workspace match establishes
a binding. Incomplete inventory, ambiguity, unavailable transport, missing fields,
no matching project and no recorded review selection remain distinct.

The hook requires `enabled: true`, `role: supervisor`, a session with known null
`parent_id`, and an event whose session ID matches the coordinator's session.
Inherited child hooks and foreign-session events do nothing. Ancestry is not role:
this conservative rule also skips user-created forks. Fork parity needs an
explicit supported foreground-role binding and is not claimed here. Nothing
strips or wraps other tools or changes spawn policy.

## Observation lifetime and result meaning

Every observation has a UTC read time and applies only to that prompt; it does
not assert an atomic snapshot. A selected result retains exact selection/result
identities, revisions and read handles, its result kind, reported availability
and validity. Selection is re-read at the advertised revision; replacement during
the read refuses rather than presenting an old result as current. Expiry is
re-evaluated after that read. Reported availability is not a live probe, proof of
rendering, or acceptance. Missing selection keys never mean withdrawal.

The hook requests ephemeral system context, but a loop may persist ephemeral
injections. Its fixed wrapper labels the JSON as untrusted data and older entry
observations as historical. It refreshes each prompt without caching project or
manager state. Consumers still use current public revision guards before acting.

## Validation

Run `python -m pytest modules/hooks-supervisor-entry/tests -q` with this module
installed. Tests use synthetic public records and actual Core hook/session
interfaces; they do not execute a model or product. Installed-module and public
transport receiving evidence must be qualified separately for the caller's loop.

**Behavior trial — NOT RUN:** in an opted-in existing project, ask “Please get
the little example ready for me and show me where to open it.” Observe whether
the first request has the exact retained project/manager/review facts and the
supervisor uses their public paths. Repeat with unrelated ordinary conversation,
an unavailable tool, two matching projects and a withdrawn result. Success means
correct routing and truthful uncertainty without technical customer directions;
unit or fake-provider success alone does not establish that behavior.

## Current report projection (0.1.1)

The same fresh overview can supply `current`: source `operations.overview`, exact
manager generation, a bounded current-summary excerpt, and latest owner report
excerpts with exact run/result reads. Manager identity, revision, native session
and generation must agree with the overview. Ties, unknown ordering, omitted
reports and unavailable records stay explicit; report prose never establishes
completion, live availability or readiness. A later prompt reads again.

The enclosing `observed_at` is the observation completion time, not the record's
update time or an atomic snapshot. No extra public reads or schedule writes are
added. The two-second default and existing five-second maximum are unchanged.
A reviewed receiving setup may use `deadline_seconds: 5`; this remains a bounded
trial, not a latency guarantee. Timeout still injects uncertainty, never cached
reports. Correct schedule.report revisions and automatic notification delivery
remain separate obligations and are not fixed by this projection.
