# MCP server

A stateless, read-only MCP surface over `../skills/` and `../runs/`.

**It contains no procedure text.** The six procedures are read from `skills/*/SKILL.md` at request
time and served as MCP **prompts**. Move `skills/` aside and `prompts/list` returns nothing — that
property is asserted in `../tools/test_mcp_server.py`, because it is the only thing preventing this
from becoming a second copy of the procedure that drifts from the first.

## Run it

```bash
uv sync --extra mcp
uv run --extra mcp python mcp_server/server.py     # stdio
```

The SDK is an optional extra. Nothing else in this repository depends on it, and the default stdlib
test run skips cleanly when it is absent.

## Client configuration

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

Inspect it interactively:

```bash
npx @modelcontextprotocol/inspector uv run --extra mcp python mcp_server/server.py
```

## What it exposes

### Prompts — the six procedures

| Prompt | Source |
|---|---|
| `run-discipline` | `skills/run-discipline/SKILL.md` |
| `declared-vs-effective` | `skills/declared-vs-effective/SKILL.md` |
| `evidence-check` | `skills/evidence-check/SKILL.md` |
| `acceptance-review` | `skills/acceptance-review/SKILL.md` |
| `run-receipt` | `skills/run-receipt/SKILL.md` |
| `blind-reconstruction` | `skills/blind-reconstruction/SKILL.md` |

The prompt name and description come from each file's frontmatter; the body is the file with
frontmatter stripped.

### Resources

Any file under `skills/*/references/`, addressed as `skill://<skill-name>/references/<file>`.

### Tools — nine, all read-only

Over `runs/`:

| Tool | Returns |
|---|---|
| `list_runs` | Every directory under `runs/` with its tier, whether a criterion exists, verdict count, evidence count, and whether an override was recorded |
| `check_run` | The **gap list** for one run — what it failed to record |
| `hash_evidence` | sha256 for every file in a run's `EVIDENCE/` directory |

Over `benchmark/`:

| Tool | Returns |
|---|---|
| `list_tests` | Every benchmark test with its category, status and environment |
| `get_test` | One test's specification **and its ground truth** |
| `get_result` | One stored result, with both evaluator outputs intact |
| `validate_result` | Whether a stored result matches the documented contract |
| `compare_runs` | Suites compared per mode, or the three arms compared within one suite |
| `replay_test` | Re-derives a result's reality verdict from its stored inputs |

`check_run` is the one that earns its place among the run tools: byte sizes detect truncation, hashes
detect substitution, and the gap list is the only output in this package that exists nowhere else.

`get_test` returns ground truth deliberately — this server is for **reading and auditing** results.
A candidate must never be given this tool, or the benchmark is worthless.

`replay_test` recomputes the **reality** half from stored inputs and reports any disagreement,
catching an evaluator that changed its mind since the run. The **workflow** half is not replayable —
the workspace it read was discarded — and the tool returns `UNKNOWN` for that half rather than
guessing.

## What it deliberately does not do

- **No write path.** Not a limitation to be lifted later — a property. A server that cannot write
  cannot corrupt a run, and cannot quietly become a control plane.
- **No state.** No sessions, no storage, no event stream, no cache. It starts with the client and
  ends with it.
- **No execution.** `run_test` and `run_suite` are deliberately absent. Running a benchmark test
  starts an agent, spends money, and writes a workspace — that is not a read. The runner is
  [`benchmark/runners/run_benchmark.py`](../benchmark/runners/run_benchmark.py), a CLI a human
  invokes. `tools/test_mcp_server.py` asserts that no tool name begins with `run_`, so this cannot
  drift by accident.
- **No receipt and no result generation.** `tools/run_receipt.py` stays a script a human runs.
  Generating an artifact and serving a procedure are different jobs with different authority.
- **No procedure text.** See above.

**Promotion trigger for `run_test`.** It may be added when all three hold: the runner is trusted
(tested, and its cost accounting verified), cost ceilings are enforced *and tested*, and the
environment isolation story is stronger than "a temp directory" — which today it is not, as
[`benchmark/README.md`](../benchmark/README.md) records. Until then this server cannot start a
process that costs money.

If you want a tool that writes, that is a new decision about what this package is — not a feature.

## Protocol notes

Built against `mcp>=1.0` (the official Python SDK). Notable: in the 2.x SDK `FastMCP` was renamed to
`MCPServer` (`mcp.server.mcpserver`); this server uses the current name.

Per the MCP roadmap, `tools/call` result shape is under active revision — the tension between
`content` and `structuredContent` has produced diverging implementations. This server returns plain
JSON-formatted text for every tool to stay unambiguous across clients, and takes no position on the
outcome.
