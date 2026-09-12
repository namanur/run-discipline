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

### Tools — three, all read-only

| Tool | Returns |
|---|---|
| `list_runs` | Every directory under `runs/` with its tier, whether a criterion exists, verdict count, evidence count, and whether an override was recorded |
| `check_run` | The **gap list** for one run — what it failed to record |
| `hash_evidence` | sha256 for every file in a run's `EVIDENCE/` directory |

`check_run` is the one that earns its place. Byte sizes detect truncation; hashes detect substitution.
The gap list is the only output in this package that exists nowhere else — it is the machine telling
you which parts of your record do not exist.

`run` arguments are confined to `runs/`; anything that resolves outside it is rejected.

## What it deliberately does not do

- **No write path.** Not a limitation to be lifted later — a property. A server that cannot write
  cannot corrupt a run, and cannot quietly become a control plane.
- **No state.** No sessions, no storage, no event stream, no cache. It starts with the client and
  ends with it.
- **No receipt generation.** `tools/run_receipt.py` stays a script a human runs. Generating the
  artifact and serving the procedure are different jobs with different authority.
- **No procedure text.** See above.

If you want a tool that writes, that is a new decision about what this package is — not a feature.

## Protocol notes

Built against `mcp>=1.0` (the official Python SDK). Notable: in the 2.x SDK `FastMCP` was renamed to
`MCPServer` (`mcp.server.mcpserver`); this server uses the current name.

Per the MCP roadmap, `tools/call` result shape is under active revision — the tension between
`content` and `structuredContent` has produced diverging implementations. This server returns plain
JSON-formatted text for every tool to stay unambiguous across clients, and takes no position on the
outcome.
