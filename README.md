# run-discipline

A portable engineering procedure, in six skills and one read-only MCP server.

> **Write down, before you start, the one command whose output would prove you failed. Keep its raw
> output. If it fails and you go ahead anyway, keep that too, and the reason.**

No daemon. No database. No workflow engine. No state.

**v0.0.1** — extracted from a personal engineering system where this has been run end to end once.

---

## The problem it addresses

When an agent does substantial work, the work is usually reconstructable and the *reasoning* is not.
Six months later you can see what changed and not why, what was verified and by whom, what was
overridden and on whose authority, and what was lost. This package is the smallest set of files that
fixes that — and nothing more.

It is not an observability platform. Every one of those already exists and does it better at scale.
This is the residue that remains when you delete everything a platform would give you: a criterion,
raw output, a verdict, a dissent, and a decision.

## The five lines

1. Before starting, name the one command that would prove you failed.
2. Run it before and after. Keep the raw output of both.
3. If it fails and you proceed anyway, record that you proceeded, and why.
4. If you cannot determine something, write `UNKNOWN`. Never write a plausible answer.
5. Keep the file. The summary is what you will forget; the command is what you can re-run.

Everything in this repository is machinery for making those five lines survive contact with real work.

---

## What is in the box

| | |
|---|---|
| **6 Agent Skills** | `skills/*/SKILL.md` — [agentskills.io](https://agentskills.io/specification) format, portable to any compatible host (Command Code, Pi, Codex, …) |
| **1 MCP server** | `mcp_server/server.py` — stateless, read-only, stdio. Serves the same six procedures as MCP **prompts** to any MCP client |
| **1 installer** | `tools/install-skills.sh` — symlinks the skills into a harness skill root |
| **1 receipt tool** | `tools/run_receipt.py` — stdlib-only, generates a run receipt and its gap list |

| Skill | Load it when | What it decides |
|---|---|---|
| `run-discipline` | Work is load-bearing, changes a system, or produces a claim someone must trust | Whether a run is warranted at all, and what it owes |
| `declared-vs-effective` | A question is about what a system actually *is* or *does* | Which layer a fact belongs to, and where a defect lives |
| `evidence-check` | A claim or a stale finding must be settled | CONFIRMED / REFUTED / UNKNOWN, with the command that decides it |
| `acceptance-review` | A finished evidence bundle needs an independent verdict | Whether the criterion is met, from the evidence alone |
| `run-receipt` | A run needs closing out, or its gaps read | What the run failed to record |
| `blind-reconstruction` | After a run, to test whether the record is usable | Whether a stranger could reconstruct what happened |

Start with **`run-discipline`**. It is the workflow and it routes to the other five.

The procedure is domain-general. NixOS and font configuration appear as *worked examples*; they are
not the subject. `declared-vs-effective` applies to any system where configuration, artifact, process
and experience can diverge — systemd, containers, Kubernetes, CI, package managers, DNS, TLS.

---

## Install

### As Agent Skills

```bash
git clone <this repo> ~/run-discipline
cd ~/run-discipline
./tools/install-skills.sh          # symlinks skills/*/ into ~/.commandcode/skills/
```

Then check discovery: `cmd skills list` should list six, with zero skipped.

To install by hand, symlink each skill **directory** into a skill root the harness reads:

```bash
ln -s "$PWD/skills/run-discipline" ~/.commandcode/skills/run-discipline
```

Some hosts also read `.agents/skills/` or `.commandcode/skills/` at a project root. A symlink into
any of them works; the skills themselves are portable.

> **Do not register these through a `settings.skills[]` array.** The highest settings layer replaces
> that array whole, so one project-level `settings.json` silently drops every global skill. Symlinks
> avoid the failure entirely.

### As an MCP server

The server needs the official MCP Python SDK. Nothing else in this repository depends on it.

```bash
uv sync --extra mcp
uv run --extra mcp python mcp_server/server.py     # speaks stdio
```

Point any MCP client at that command. Example client configuration:

```json
{
  "mcpServers": {
    "run-discipline": {
      "command": "uv",
      "args": ["run", "--extra", "mcp", "python", "mcp_server/server.py"],
      "cwd": "/absolute/path/to/run-discipline"
    }
  }
}
```

Inspect it interactively with `npx @modelcontextprotocol/inspector uv run --extra mcp python mcp_server/server.py`.

---

## Quick start

There is nothing to configure. A first run:

```bash
mkdir -p runs/2026-01-01-example
$EDITOR runs/2026-01-01-example/TASK.md      # request, criterion, tier — see references/task-frontmatter.md
mkdir -p runs/2026-01-01-example/EVIDENCE
fc-match monospace > runs/2026-01-01-example/EVIDENCE/before.txt   # whatever proves the claim
# ... do the work ...
fc-match monospace > runs/2026-01-01-example/EVIDENCE/after.txt
python3 tools/run_receipt.py --run runs/2026-01-01-example
```

Then read the **gap list** at the bottom of `RECEIPT.md`. That list — not the summary — is the
product. It is the machine telling you which parts of your record do not exist.

`runs/` ships empty on purpose. A synthetic example run would be a fabricated record, which is the
one thing this procedure forbids.

---

## Run the benchmark

The benchmark measures whether the procedure helps, by running the same fixtures against three arms:
no procedure, the five lines, and the six skills.

```bash
# plan only — prints the run count and an estimate, spends nothing. Always first.
python3 benchmark/runners/run_benchmark.py --test FP-001 --mode all --dry-run

# run it, with a ceiling
python3 benchmark/runners/run_benchmark.py --test FP-001 --mode all --budget-usd 1.50

# re-render a stored suite after changing policy, without spending again
python3 benchmark/runners/run_benchmark.py --summarise <suite>

# regenerate the generated half of the Status section above
python3 benchmark/runners/run_benchmark.py --status
```

Results land in `benchmark/results/<suite>/`: one `RESULT.md` per (test, arm), both raw evaluator
outputs, and a `SUITE.md` that applies [`benchmark/policy.md`](benchmark/policy.md) mechanically.
See [`benchmark/README.md`](benchmark/README.md) for the design and its limits.

---

## Layout

```
run-discipline/
├── README.md                  you are here
├── WHY.md                     the rationale, the decision record, and what this refuses to be
├── PROCESS.md                 one task, start to finish, and the files that exist at each step
├── skills/                    the source of truth for all procedure text
│   ├── README.md
│   └── <six skills>/SKILL.md
├── benchmark/                 the judge — tests, environments, ground truth, two evaluators
│   ├── policy.md              the rules, including the ones that can kill this package
│   └── tests/ ground-truth/ environments/ evaluators/ runners/ results/
├── mcp_server/                reads skills/ and benchmark/ — holds no procedure text of its own
├── tools/
│   ├── install-skills.sh
│   ├── run_receipt.py
│   ├── test_mcp_server.py
│   └── test_benchmark.py
└── runs/                      where runs go (empty until you make one)
```

**One source of truth.** The skills are the only copy of the procedure. The MCP server reads them at
request time; move `skills/` aside and `prompts/list` returns nothing. That property is a test, not a
promise — see `tools/test_mcp_server.py`.

---

## Verify

```bash
python3 -m unittest discover -s tools -t tools            # 49 tests; MCP tests skip without the extra
.venv/bin/python -m unittest discover -s tools -t tools   # all 49 run, after uv sync --extra mcp
```

| Check | Pass condition |
|---|---|
| Skill loading | All six load; every `name` matches its directory name |
| Description discipline | Every description is ≤1024 chars and names when the skill should *not* apply |
| Provenance | Every skill carries `derived_from`, `adaptation_reason`, `verification`, `known_limitations` |
| Prompts round-trip | Each MCP prompt returns its `SKILL.md` body with frontmatter stripped |
| **No duplication** | With `skills/` absent, the server exposes **zero** prompts |
| **Read-only** | Calling every tool leaves every byte under `runs/` unchanged |
| **No execution tool** | No MCP tool name begins with `run_`; `run_test` is absent by design |
| Path confinement | `check_run` refuses paths outside `runs/` |
| **Evaluator separation** | The reality and workflow evaluators share no input argument |
| **`UNKNOWN` costs something** | Every battery category forbids `UNKNOWN` somewhere |
| **No answer key in the room** | No environment file declares an expected verdict |
| **Fixture honesty** | Every ground truth declares what would falsify it |

---

## What this deliberately is not

No event store. No knowledge graph. No memory system. No orchestrator. No scheduler. No dashboard.
No embeddings. No multi-agent swarm. No write path in the server.

Each of those exists, is maintained by someone else, and solves a problem this does not have. The
rule that produced this list is simple: **if an existing system already does it, adopt that system.**

The MCP server is read-only by construction. Any tool that writes would be a new decision about what
this package is, not a feature added to it.

---

## Status — v0.0.2

Two accounts, deliberately kept apart. The first says what the package *is*; the second says what has
been *measured*. A polished implementation section must not be able to pass for a result.

### Implementation status

| | |
|---|---|
| Procedure demonstrated | **YES** — one run, end to end, on a real read-only task |
| Read-only workflow | **YES** |
| Machine-change workflow | **NO** — never exercised, in this package or its origin |
| Rollback tested | **NO** — `rollback_tested` has never been filled by any run |
| Override recorded | **NO** — no run has ever recorded one |
| Independent disagreement | **NO** — the one review agreed with every verdict |
| Receipt robustness | **NO** — `tools/run_receipt.py` has no test suite and two known crash paths |

### Benchmark status

Generated by `benchmark/runners/run_benchmark.py --status`. A hand-maintained number is a number that
rots, and this one exists so the section above cannot quietly gain credit from the section below.

<!-- benchmark-status:start -->

| | |
|---|---|
| Synthetic suite | 6 built / 12 specified |
| Comparative suites run | 2 |
| Latest suite | v0.0.2-first (3 scored run(s) across 3 mode(s); candidate correct on 1) |
| Real-world runs | 0 |

<!-- benchmark-status:end -->

**Falsified by.** If no skill is activated across the next three real tasks · if the MCP server is
never connected by a second client · if either surface grows past ~600 lines without a newly
demonstrated procedure · if the `mcp` dependency's maintenance is ever paid without a second
consumer · if `candidate ≤ minimal` across a benchmark suite. On any of those, delete rather than
maintain. [`benchmark/policy.md`](benchmark/policy.md) turns that last condition from a promise into a
comparison the runner performs.

See [WHY.md](WHY.md) for how that list was arrived at and [PROCESS.md](PROCESS.md) for the walkthrough.
