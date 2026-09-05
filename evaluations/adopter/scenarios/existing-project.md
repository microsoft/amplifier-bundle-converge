You have a project you have been working on for a while -- `sensorlog`, a
small Python command-line tool at `/workspace/existing-project`. It works,
its tests pass, and its README names two things nobody has decided yet. It
has no vision document, no contracts, and no AGENTS.md; you have simply been
building it.

Someone showed you Converge and you want to adopt it for this project without
throwing away what is there. All you have is one document: the Converge
README, saved at `/workspace/CONVERGE-README.md`. You have never used
Converge before. You do not know how it is built, and you do not want to --
you want to use it.

Read that README, then get the project adopted. As you understand it from the
README, that means:

- Converge is installed in your Amplifier CLI.
- A **manager session** is running against `/workspace/existing-project`.
- Someone has actually looked at the code that is there before proposing
  anything about it -- you should not be handed a vision for a project nobody
  read.
- The project has a **vision** written down, and at least one **contract**
  that says something true and checkable about *this* code.
- Nothing was ratified without you saying so.
- The project's contract check exists, and there is work in a queue that names
  the contracts it serves -- specifically, work that would bring the existing
  code into line with the new contracts.

Work with the agent to get there. You are the intent steward: you decide, you
answer questions, you say yes or no. Answer questions about the project from
what you can see in the repository; you know this code.

When you cannot get any further, conclude. Be specific about what you tried,
what worked, what did not, and -- most useful of all -- **every point where
the README did not tell you what to do next and you had to guess, experiment,
or give up**. Those are the finding. Do not paper over them.

Conclude with `verdict=success` only if all six bullets above are actually
true, and you saw them be true. If you got partway, conclude
`verdict=failure` and say exactly how far you got and what stopped you. A
clear, honest account of where you got stuck is worth far more here than a
generous verdict.
