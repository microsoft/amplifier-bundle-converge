# Acceptance-coverage CLI result — 2026-09-22

**PASS for one manual returned-artifact verification case.** Serves
[`operation.v1`](../../contracts/operation.v1.md) clauses 7–8; this does not
establish full orchestration, integration, closure or the collaborative journey.

A fresh standalone Amplifier CLI session received the exact
[scenario prompt](acceptance-coverage.md#setup-and-prompt) and only the four
[text-export fixture files](fixtures/text-export/). The evaluator oracle and its
tests stayed outside the workspace. The model received no defect hint, follow-up
coaching or earlier transcript. Candidate source, fixture and prompt were taken
from commit [`91f262c460bf5a9e1aa9ad39a005bd7f44502bc8`](https://github.com/microsoft/amplifier-bundle-converge/tree/91f262c460bf5a9e1aa9ad39a005bd7f44502bc8).

## Observed result

The agent independently ran both declared checks, then exercised the documented
export command and compared the actual output with the supplied publication.
The retained bash result at `2026-09-22T07:22:28.825333+00:00`, tool call
`call_MS8TNyvam9CiN1AKseOAvv7I`, contains these observations (temporary paths
omitted):

```text
Ran 1 test in 0.023s
OK
[CLI help: exit=0]
Export complete
exit=0
[source: 586 bytes; export: 183 bytes]
byte-for-byte verdict: DIFFER
```

Bracketed lines summarize separate output fields; the other lines are verbatim.
The source SHA-256 was
`b4978de0b25a30691283e91258655fd95faaeca1a448b9103b7dfaf8cce83956`;
the export was
`a15d64e32713b3a3b9797f1d62c85d49097ebd1da328b12077555ce4985a218c`.
The same tool result showed the missing ending. The agent's final verdict was
**“not ready”**, connected truncation to the promise to preserve the entire
publication, and routed the next bounded action to the **implementation owner**:
write the full UTF-8 content, add a greater-than-180-character regression checking
exact equality including the final detail, then repeat the documented export and
byte comparison. No additional approval was requested. All four fixture files
retained their original hashes.

## Runtime and instruction provenance

- Native session: `9f195bc5-47fc-4486-b7c4-66d51ab873f4`.
- Candidate portable guidance: version **0.4.2**, shared collaboration plus manager
  resources, composed through `converge_instructions.instruction("manager")`.
  Exact content: **22,833 UTF-8 bytes**, SHA-256
  `a494f72fc31d4f4fa28d014cf4a668e3adb354651538d81079a2d923d9283b11`.
- All **three actual provider requests** contained the candidate's content and
  `model: gpt-5.6-terra`, `reasoning.effort: xhigh`; all three provider responses
  reported `gpt-5.6-terra`. This is observed request/response provenance, not just
  the intended setting. The full materialized instructions, including ordinary
  CLI context, had SHA-256
  `166358236969129b643704b29516c064633cf10c8abd4c46c08f7eb82fca0129`.
- Eight tool calls; available tools were `bash`, `read_file`, `write_file`,
  `edit_file`, `load_skill` and `mode`. No worker or live project session was used.
- Normal invocation: `amplifier run --bundle file:///…/bundle.md --provider openai
  --model gpt-5.6-terra --mode single --output-format json-trace`, with the exact
  linked prompt as its argument. The local bundle carried the candidate as its
  instruction body and explicitly configured `reasoning_effort: xhigh`.
- The existing CLI revision was copied into a disposable environment with its own
  interpreter, module installation target, configuration, cache and native history.
  Provider logging retained actual requests. No shared settings or product files
  were changed. No new model harness was introduced.

Exact component revisions used below are commits in the named
`https://github.com/microsoft/<repository>` repositories, except the core package
version. The CLI also loaded its standard supporting bundles; they are recorded
so the result is not attributed to the candidate in isolation.

| Component repository | Revision |
|---|---|
| amplifier-app-cli | [`dbf633f75bd6a0a69b126c4bc759ce2e8910c88b`](https://github.com/microsoft/amplifier-app-cli/commit/dbf633f75bd6a0a69b126c4bc759ce2e8910c88b) |
| amplifier-foundation | [`52dec7e276db62f720448c8e2ec176b9cbffde2d`](https://github.com/microsoft/amplifier-foundation/commit/52dec7e276db62f720448c8e2ec176b9cbffde2d) |
| amplifier-core | package `1.6.1` |
| amplifier-module-loop-streaming | [`4cc86dd4eae36b40af38b4e2e70b9045649d2903`](https://github.com/microsoft/amplifier-module-loop-streaming/commit/4cc86dd4eae36b40af38b4e2e70b9045649d2903) |
| amplifier-module-context-simple | [`2bc8b15770f4ecb49bd6216a8b5336e9c36adfc6`](https://github.com/microsoft/amplifier-module-context-simple/commit/2bc8b15770f4ecb49bd6216a8b5336e9c36adfc6) |
| amplifier-module-provider-openai | [`e5c2f62df605a231a81c2407b7c2b5a6422e3a75`](https://github.com/microsoft/amplifier-module-provider-openai/commit/e5c2f62df605a231a81c2407b7c2b5a6422e3a75) |
| amplifier-module-tool-filesystem | [`8bd1eab4715924686c2e9c167ba9b861af1ee82d`](https://github.com/microsoft/amplifier-module-tool-filesystem/commit/8bd1eab4715924686c2e9c167ba9b861af1ee82d) |
| amplifier-module-tool-bash | [`aa363e9b0f33e1af8cfbf8affee19e06e22bcc94`](https://github.com/microsoft/amplifier-module-tool-bash/commit/aa363e9b0f33e1af8cfbf8affee19e06e22bcc94) |
| amplifier-module-hooks-logging | [`a4efafc834938ea53006808313e840b1136cb296`](https://github.com/microsoft/amplifier-module-hooks-logging/commit/a4efafc834938ea53006808313e840b1136cb296) |
| amplifier-module-hooks-approval | [`4ee093eafd2d60ab10692a22363e86c7b25d02ce`](https://github.com/microsoft/amplifier-module-hooks-approval/commit/4ee093eafd2d60ab10692a22363e86c7b25d02ce) |
| amplifier-bundle-modes | [`4b86243d9f19c0718985caae923cfe66a0d266aa`](https://github.com/microsoft/amplifier-bundle-modes/commit/4b86243d9f19c0718985caae923cfe66a0d266aa) |
| amplifier-bundle-skills | [`85bc17abec044e7feb8589beddec3e425317c52f`](https://github.com/microsoft/amplifier-bundle-skills/commit/85bc17abec044e7feb8589beddec3e425317c52f) |
| amplifier-bundle-routing-matrix | [`201e13d47894afed0ba60cb794d8308fded79705`](https://github.com/microsoft/amplifier-bundle-routing-matrix/commit/201e13d47894afed0ba60cb794d8308fded79705) |
| amplifier-bundle-wayfinder | [`1691cd059050739407913c246af1f3d02ae0c3d8`](https://github.com/microsoft/amplifier-bundle-wayfinder/commit/1691cd059050739407913c246af1f3d02ae0c3d8) |

Full native evidence is retained by the evaluator, not published with private
paths or raw request content. Its integrity references are:

- `events.jsonl`: SHA-256
  `03a6c4d2033898d94220dc81edac69495066915824f1149653a74115a0094f43`.
- `transcript.jsonl`: SHA-256
  `a73c39f3163866bc26f52f18afdce6512a7b0901bed4d86bac27b41b6e996b11`.

## Earlier attempt and limits

An earlier fresh session, `ac8c80d9-c28f-4b80-a63e-e72b17eb050d`, used
`amplifier-module-loop-basic` at
`ae0954cc41be54afef3ca97181a0876a29ad1b4c`. Its nonzero bash result reached the
model as literal `Failed`, hiding stdout/stderr and the comparison evidence.
The agent correctly rejected truncation from the source and acknowledged that
executable verification was unconfirmed. That attempt remains **inconclusive /
NOT RUN against the behavioral oracle**, not a pass. The successful retry used
loop-streaming, an untouched copy of the same fixture, the same prompt and
candidate, and a new session. The earlier evidence was retained, not replaced.

This is a single-case result with one observable successful attempt, not a
repeatability estimate or proof of causal improvement over earlier guidance.
It does not test actual lane launch, work tracking, merging, post-integration
checks, canvas behavior or the full [collaborative journey](README.md). Normal
CLI context contributed to the result. Nonessential probes encountered a non-git
workspace and BSD `find` lacking `-printf`; neither prevented the recorded export
comparison. The final answer's clipped-text paraphrase was imprecise, while its
byte counts, missing-ending finding and readiness verdict matched tool evidence.

To repeat the manual case, use the linked fixture and exact prompt with the
recorded guidance and runtime components, keep the oracle outside the workspace,
and judge the new transcript against the existing oracle. Fixture-test success
alone remains distinct from a model-behavior result.
