# Skills

Six Agent Skills in [agentskills.io](https://agentskills.io/specification) format. This directory is
the **source of truth for all procedure text** in this repository — the MCP server reads it at request
time and adds nothing.

```bash
../tools/install-skills.sh        # symlinks each skill directory into ~/.commandcode/skills/
cmd skills list                   # expect six, zero skipped
```

## The six

| Skill | Load it when | What it decides |
|---|---|---|
| `run-discipline` | Work is load-bearing, changes a system, or produces a claim someone must trust | Whether a run is warranted at all, and what it owes |
| `declared-vs-effective` | A question is about what a system actually *is* or *does* | Which layer a fact belongs to, and where a defect lives |
| `evidence-check` | A claim or a stale finding must be settled | CONFIRMED / REFUTED / UNKNOWN, with the command that decides it |
| `acceptance-review` | A finished evidence bundle needs an independent verdict | Whether the criterion is met, from the evidence alone |
| `run-receipt` | A run needs closing out, or its gaps read | What the run failed to record |
| `blind-reconstruction` | After a run, to test whether the record is usable | Whether a stranger could reconstruct what happened |

Start with `run-discipline`; it routes to the other five.

**Nothing here is machine- or vendor-specific.** NixOS and font configuration appear as worked
examples because that is where the procedure was first applied. `declared-vs-effective` applies to any
system where configuration, artifact, process and experience can diverge — systemd, containers,
Kubernetes, CI, package managers, DNS, TLS.

## Installing by hand

Symlink the **directory**, not the file — a skill is a directory, and its `name` must equal its
directory name.

```bash
ln -s "$PWD/run-discipline" ~/.commandcode/skills/run-discipline
```

Other hosts read other roots (`~/.agents/skills/`, `.commandcode/skills/`, `.agents/skills/` at a
project root). The skills are portable; only the root differs.

> **Never register these through a `settings.skills[]` array.** The highest settings layer replaces
> that array whole, so a single project-level `settings.json` silently drops every global skill.
> Symlinks do not have this failure mode.

## Verify

| Check | Command | Pass |
|---|---|---|
| Discovery | `cmd skills list`, then `--debug` | Six listed, zero skipped |
| Promotion | `ls -la ~/.commandcode/skills/` | Six symlinks into this repository |
| Activation | `/run-discipline` in a session | Body loads; `references/` loads only when the body links it |
| **Discrimination** | an ordinary prompt — *"add a dark mode toggle"* | **No skill activates.** This is the check that matters day to day |
| Provenance | `grep -L derived_from skills/*/SKILL.md` | No output |
| No duplication | move `skills/` aside, call `prompts/list` on the MCP server | Zero prompts |

The first five are manual; the last two are enforced by `../tools/test_mcp_server.py`.

## Provenance

Every skill carries four fields in its `metadata` block. They are the reason a reader can tell what
was adopted, what was changed, and what is not known to work.

| Field | Holds |
|---|---|
| `derived_from` | The sources this came from |
| `adaptation_reason` | What was changed, and why |
| `verification` | How we know it works — the specific observation |
| `known_limitations` | What it cannot do, stated inside the skill itself |

A missing field fails the test suite.

## Adding a seventh

The rules, in the order they matter:

1. **A demonstrated procedure plus a live trigger.** Not a subject area, not a plausible need. Every
   skill here earned its place by running at least once and doing measurable work.
2. **A description that discriminates.** It is the only text visible before the model decides to load
   the skill. State what it does, when it applies, and **when a similar request should not activate
   it**. The boundary clause is required by the test suite, not optional.
3. **Under ~500 lines.** Move conditional detail into `references/`, and link each reference from the
   body with the condition under which to read it. There is exactly one reference file in this
   package, added only where the content is both conditional and machine-parsed.
4. **Do not restate what lives elsewhere.** A reusable procedure belongs in a skill; a standing
   identity — *"you did not write this work"* — belongs in a named agent; a deterministic check
   belongs in a script. A skill that repeats an agent's stance will drift from it.
5. **Do not restate what is enforced mechanically.** If a hook or permission rule enforces something,
   the skill should not also describe it as a rule. Duplication drifts; the enforced version is the
   true one.
6. **Keep discovery cheap and precise.** Metadata for every skill is in context at startup. A vague
   description costs tokens on every request and selects wrongly.

## What is deliberately absent

Five skills were designed for this procedure and are not built: `ownership-audit`,
`architecture-review`, `security-review`, `research-discipline`, `teach-completion`. Each belongs to a
role that has never run, so none has a demonstrated reason to exist yet.

The full reasoning, the rejected alternatives, and the conditions under which this whole package
should be deleted are in [../WHY.md](../WHY.md).
