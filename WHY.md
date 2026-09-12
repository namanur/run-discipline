# Why this exists, and why it is this small

## The question it answers

> Reconstruct, months later: what happened, why, what evidence supported it, what was verified, who
> disagreed, what you decided, and how to recover.

That question was first approached as a build. A system was designed to answer it: an ingest path, an
event taxonomy, validated claims, a promotion gate, a provenance-carrying knowledge format, and a
graph over the top. The design was researched for two passes and then killed, deliberately, when a
substitution test checked its seventeen intended capabilities against roughly twenty existing systems
from primary sources at pinned commits:

**Eight were already solved, seven partially solved, one composable, one unsolved.** Roughly 70% of
the intended architecture already shipped and was maintained by someone else.

The single genuinely unsolved capability was narrow: *stored, re-runnable, per-claim falsifiers*. That
is the residue this repository is built from. Everything else was deleted from the design.

## Why a procedure and not a program

What survived the kill was not a component. It was a convention:

| Primitive | Minimal representation |
|---|---|
| Run identity | a directory slug |
| Human criterion | an authored acceptance statement, written before the work |
| Evidence | raw command + exact output |
| Claim ledger | claim · grade · source · status · supersedes |
| Independent review | a verdict from the evidence alone |
| Human gate | an explicit ruling, and any override, recorded |
| Receipt | a deterministic summary, including what it could not determine |
| Recovery pointer | the state before, the state after, and whether rollback was tested |
| Provenance | the source path or hash of anything cited |
| Uncertainty | the literal `UNKNOWN` |

None of these needs a program. They need a file, a habit, and one person willing to write a sentence
they cannot later move.

## Why six skills, and not nine or fourteen

Two separate lists of skills were written for this procedure before any existed. This package takes
the intersection of both, filtered by one rule: **a demonstrated procedure plus a live trigger.**

| Built | Why it qualified |
|---|---|
| `run-discipline` | The convention itself; every other skill is reached through it |
| `declared-vs-effective` | The layer split did real work on a real defect, and the original claim described the *wrong layer* |
| `evidence-check` | It re-ran every decisive command and overturned a wrong recorded grade — a measured effect, not an asserted one |
| `acceptance-review` | The review added refinements the collector missed and listed what the evidence could not establish |
| `run-receipt` | Its gap list caught two unset fields and is the only output that exists nowhere else |
| `blind-reconstruction` | Run twice with recorded results; it converts "a reader could reconstruct this" from a claim into a measurement |

| Not built | Why not |
|---|---|
| `ownership-audit` | Belongs to an agent that was never installed; never run |
| `architecture-review` | The planning phase has never executed |
| `security-review` | Its agent was never installed |
| `research-discipline` | The research it served is complete and retained elsewhere |
| `teach-completion` | The teaching phase has never happened |

None of those five is a bad idea. Each lacks a *demonstrated reason to exist*, which is the same rule
that removed four candidate agents from the roster. Add them when a task demands one, not before.

## Why both a skill surface and an MCP surface

| Surface | Reaches | Cost |
|---|---|---|
| Agent Skills | Anything implementing agentskills.io — Command Code, Pi, Codex | A markdown file. Progressive disclosure keeps discovery at ~100 tokens per skill |
| MCP | Any MCP host — desktop clients, editors, other agents | One optional Python dependency |

**The server contains no procedure text.** It reads `skills/*/SKILL.md` at request time and serves the
bodies as MCP prompts. This is enforced as a test: move `skills/` aside, restart the server, and
`prompts/list` returns nothing.

That constraint is the whole reason two surfaces are affordable. The failure mode this avoids is real
and was measured in the originating system: 17,277 lines of prose documenting 1,120 lines of code,
across five restatement layers, where the same fact appeared in up to ten documents. Prose volume was
not neutral — it was the reason the system had become unusable for its own author and the reason its
documents kept drifting from its code.

## Why MCP is not the thing that was previously rejected

The originating system's forbidden list says, flatly, *"An MCP or WebMCP server → not built."* That
line is correct and this package does not overturn it. Its scope is narrower than it reads.

That entry came from a list of capabilities a proposed **system** would have had. It answered one
question: *should there be an MCP server as the interface to an event store and a knowledge graph?*
The answer was no, and it is still no.

It never evaluated a stateless, read-only adapter that serves a procedure already written down.
Three things make that a different question:

1. **MCP is now stateless.** Protocol-level sessions and the initialization handshake were removed
   (SEP-2575, SEP-2567). "A server" no longer implies "a service holding state."
2. **A local server is a subprocess.** Speaking stdio, it is not a daemon, holds no port, and stores
   nothing. It starts when a client starts and dies when the client does.
3. **MCP is converging on progressive discovery** — a stated roadmap priority, for the same reason
   skills use progressive disclosure: loading an entire catalog before the first question is asked
   makes tool selection worse, not better.

What this server creates is nothing. What it serves already exists in `skills/`.

## Where content belongs

This is the routing rule, and applying it is most of the design work:

| Content | Correct primitive | Because |
|---|---|---|
| A deterministic check | A script or tool | It must produce the same answer every time |
| A reusable procedure | **A skill** | Loaded on demand, cheap to discover |
| A standing identity or stance — *"you did not write this work"* | A named agent | It is a role, not a set of steps |
| A short isolated investigation | A subagent | Burns context that should not be kept |
| A durable multi-step process | A runtime — **only when unattended or long-running** | If a human is present at every step, a runtime is a liability |
| A decision that changes what is true | A human | No model may confer authority on itself |

The most important line is negative: **do not build a new primitive when the environment already
provides one.**

## What this deliberately refuses to be

An event store · a session model · a knowledge format · a graph · an observability layer · an
orchestration runtime · a scheduler · a control plane · a dashboard · a vector store · a memory
system · a multi-agent swarm · a promotion gate · a server with a write path.

Every one of those is either already shipped elsewhere or is not justified by any problem observed
here. The list is checked whenever something is proposed, and a "yes" is a stop, not a debate.

## Honest limitations

| | |
|---|---|
| **n = 1** | The procedure has run once, on one read-only task. Nothing here is a rate. |
| **The change tier is untested** | Base state, result state, and `rollback_tested` exist as fields and have never been filled by a run that changed anything. |
| **No override has ever been recorded** | The override is the one genuinely novel artifact here, and the one the process has never exercised. |
| **Reviewer independence is unverifiable** | The harness does not record which model served a subagent. The honest value is `UNKNOWN`, and this package prints it rather than inferring. |
| **The receipt is untested** | 425 stdlib lines, two known crash paths on malformed input, silent when it fails. Its gap list is valuable; its arithmetic should not be trusted without a check. |
| **Two skills are one person's synthesis** | `declared-vs-effective` and `blind-reconstruction` generalise from a single domain. They are stated generally and demonstrated narrowly. |

## Falsified by

Any of these, and this package should be deleted rather than maintained:

- No skill is activated across the next three real tasks.
- The MCP server is never connected by a second client.
- Either surface grows past ~600 lines without a newly demonstrated procedure.
- The `mcp` dependency's maintenance is ever paid without a second consumer.
- The procedure runs on a real change and the ceremony outweighs the reconstruction value.

The research this came from is retained in the originating system either way, so deleting the package
loses nothing that was not already written down.
