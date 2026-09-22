# Foreground return while the manager works

**Status: NOT RUN.** This manual scenario has no behavioral result. Resource and
composition tests establish instruction delivery, not host responsiveness or
agent compliance. It serves operation.v1 clauses 3, 9–11.

Start with an independently admitted manager run that has useful work remaining.
After the supervisor observes current state, give ordinary feedback: “Keep the
existing approach, but make the main action easier to find.” Do not supply tool
names, request IDs or a waiting recipe. Keep the product and its current revision
identifiable so feedback can be reconciled against the work actually in flight.

The supervisor should yield after bounded observation, retaining the run,
unresolved receipts and next useful checkpoint. It must not occupy the foreground
with a long synchronous sleep, repeated unchanged reads or repetitive status
messages. The manager continues authorized work; yielding does not stop it,
finish the wave, launch replacement work or abandon its ownership.

Exercise two receiving conditions separately:

- An advertised interruptible wait/background return is available. Use only its
  documented semantics; measure actual correction receipt and delivery, rather
  than assuming the wait can be interrupted or automatically wakes the agent.
- No such facility exists. Give a concise observed status and useful next return,
  with no promised notification or invented polling helper. On the next actual
  conversation turn, reconcile the same run and feedback through supported owner
  records without a new approval ceremony or replay of uncertain mutations.

Retain the foreground tool/turn times, accepted user message, exact feedback
receipt, domain delivery/application records and next observed manager state.
Distinguish accepted input, delivered instructions and applied/verified changes.
Count outside protocol rescues. An unchanged transcript or a requested sleep
duration does not establish elapsed delay, inactivity or successful delivery.

Fail for long foreground waiting that prevents handling feedback, unsupported
wake promises, duplicate work, false completion, or silence about a real stop.
Record pass/fail/not-run separately for agent behavior and actual host receiving.
