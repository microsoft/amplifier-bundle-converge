The agent is the **Amplifier CLI**, already installed in this environment.

This guide describes the CLI and nothing else. It deliberately says nothing
about Converge -- no bundle name, no install command, no mode, no workflow.
The only Converge documentation you have is the README at the path your
scenario names, and finding your way from it is the whole point of the
exercise. If something you need is not in that README, that is a finding to
report, not a gap for this guide to fill.

## Start the agent once (persistent tmux session)

Launch the interactive session inside a detached tmux session named `agent`,
in your scenario's project directory:

    tmux kill-server 2>/dev/null; tmux new-session -d -s agent -x 220 -y 50 'cd <project-dir> && amplifier'

The session is slow to start (allow 20-30 seconds). Poll the screen until the
input prompt `>` appears before sending anything:

    tmux capture-pane -p -t agent

A warning that the terminal does not support cursor position requests (CPR)
is harmless; ignore it.

## Send each message into the same session

    tmux send-keys -t agent '<your message>' Enter

Replies take 20-90 seconds. Poll until the `>` prompt returns at the bottom
with no spinner running:

    tmux capture-pane -p -t agent

To read a reply that scrolled past the visible screen:

    tmux capture-pane -p -t agent -S -400

For a message with tricky quoting, write it to a file first:

    printf '%s' '<your message>' > /tmp/msg.txt
    tmux send-keys -t agent "$(cat /tmp/msg.txt)" Enter

## Slash commands

The CLI takes slash commands typed at the prompt like any other message --
`/help` lists what this session actually has. Send them the same way:

    tmux send-keys -t agent '/help' Enter

Some commands are gated: the first attempt is refused with a warning and
sending it a second time confirms it. If a command appears to do nothing,
capture the screen and read what it said before assuming it failed.

## Shell commands are yours to run too

You are a person at a terminal. Running `amplifier ...` non-interactively,
installing something, `ls`, `git status`, `cat` -- all fair game, as a real
adopter would. But the CONVERSATION with the agent must stay in the one tmux
session (below).

## Continuity (critical)

Every follow-up MUST go to the SAME `tmux ... -t agent` session. Do NOT run
`amplifier` again for a follow-up, do NOT start a second tmux session, and do
NOT use `amplifier run "..."` to continue a conversation -- each of those
starts a fresh session with no memory, and silently breaks the conversation.
One scenario = one tmux `agent` session from start to finish. The agent
remembering your earlier turns is how you confirm you are still in it.

An exception: if you install something that changes the session's
capabilities, a restart may be necessary for it to take effect. If you
restart, say so in your conclusion and start the new session the same way.
