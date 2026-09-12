#!/usr/bin/env python3
"""Generate runs/<id>/RECEIPT.md from the run's authored files and the session transcript.

Read-only outside its single output file. Stdlib only. This is the one piece of
software the kill verdict explicitly permits (VERDICT.md:55-58).

Usage:
    tools/run_receipt.py --session ~/.commandcode/projects/<slug>/<id>.jsonl \
                         --run runs/<run-id>

Authored facts come from TASK.md. Derived facts come from the transcript, the
filesystem, and git. The receipt stores nothing and interprets nothing: it reports
what is on disk and names every gap it can see.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

UNKNOWN = "UNKNOWN — not observable"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
USAGE_RE = re.compile(r"<usage>(.*?)</usage>", re.DOTALL)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _consume_block(lines: list[str], start: int, parent_indent: int):
    block = []
    index = start
    while index < len(lines) and (not lines[index].strip() or _indent(lines[index]) > parent_indent):
        block.append(lines[index])
        index += 1
    return block, index


def _parse_entry(lines: list[str], index: int, rest: str, line: str):
    """Parse the value beginning with `rest` on lines[index]; return (value, next_index)."""
    if rest in (">", "|", ">-", "|-"):
        block, cursor = _consume_block(lines, index + 1, _indent(line))
        return " ".join(part.strip() for part in block if part.strip()), cursor
    if rest == "":
        block, cursor = _consume_block(lines, index + 1, _indent(line))
        return parse_lines(block), cursor
    if rest.startswith("[") and rest.endswith("]"):
        return [item.strip().strip("\"'") for item in rest[1:-1].split(",") if item.strip()], index + 1
    if rest.startswith("{"):
        return rest, index + 1
    return rest.strip("\"'"), index + 1


def parse_lines(lines: list[str]):
    """Parse the TASK.md frontmatter subset: mappings, sequences, block scalars."""
    if not lines:
        return {}
    sequence = lines[0].lstrip().startswith("- ")
    value: object = [] if sequence else {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if sequence:
            text = line.strip()[2:]
            if ":" not in text:
                value.append(text)
                index += 1
                continue
            key, _, rest = text.partition(":")
            item = {}
            item[key.strip()], index = _parse_entry(lines, index, rest.strip(), line)
            while (
                index < len(lines)
                and lines[index].strip()
                and _indent(lines[index]) > _indent(line)
                and not lines[index].lstrip().startswith("- ")
            ):
                sub = lines[index].strip()
                if ":" not in sub:
                    index += 1
                    continue
                sub_key, _, sub_rest = sub.partition(":")
                item[sub_key.strip()], index = _parse_entry(lines, index, sub_rest.strip(), lines[index])
            value.append(item)
        else:
            text = line.strip()
            if ":" not in text:
                index += 1
                continue
            key, _, rest = text.partition(":")
            value[key.strip()], index = _parse_entry(lines, index, rest.strip(), line)
    return value


def parse_frontmatter(text: str) -> dict:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    parsed = parse_lines(match.group(1).splitlines())
    return parsed if isinstance(parsed, dict) else {}


def field(frontmatter: dict, path: str):
    node: object = frontmatter
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def fmt(value) -> str:
    if value is None:
        return "**missing**"
    if isinstance(value, list):
        return ", ".join(fmt(item) for item in value) or "(none)"
    if isinstance(value, dict):
        return "; ".join(f"{key}={fmt(item)}" for key, item in value.items())
    return str(value)


def read_transcript(session_path: Path | None) -> dict:
    stats = {
        "records": 0, "messages": 0, "human_msgs": 0, "tool_results": 0,
        "models": set(), "tools": {}, "agents": [], "cost_usd": 0.0,
        "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
        "cache_write_tokens": 0, "peak_input_tokens": 0,
        "first_ts": None, "last_ts": None, "parse_errors": 0,
    }
    if not session_path or not session_path.exists():
        return stats
    agent_index = {}
    with session_path.open() as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                stats["parse_errors"] += 1
                continue
            stats["records"] += 1
            timestamp = record.get("timestamp")
            if timestamp:
                stats["first_ts"] = stats["first_ts"] or timestamp
                stats["last_ts"] = timestamp
            if record.get("type") != "message":
                continue
            stats["messages"] += 1
            message = record.get("message", {})
            meta = message.get("meta", {}) or {}
            if meta.get("source") in ("user", "steering"):
                stats["human_msgs"] += 1
            for item in message.get("content", []) or []:
                if not isinstance(item, dict):
                    continue
                kind = item.get("type")
                if kind == "tool_use":
                    name = item.get("name", "?")
                    stats["tools"][name] = stats["tools"].get(name, 0) + 1
                    if name == "agent":
                        payload = item.get("input", {}) or {}
                        entry = {
                            "type": payload.get("subagent_type", "?"),
                            "description": payload.get("description", ""),
                            "usage": {},
                        }
                        stats["agents"].append(entry)
                        agent_index[item.get("id")] = entry
                elif kind == "tool_result":
                    stats["tool_results"] += 1
                    entry = agent_index.get(item.get("tool_use_id"))
                    if entry is None:
                        continue
                    text = " ".join(
                        part.get("text", "") for part in item.get("content", [])
                        if isinstance(part, dict)
                    )
                    match = USAGE_RE.search(text)
                    if match:
                        entry["usage"] = {
                            key: value
                            for key, value in re.findall(r"(\w+):\s*([\d.]+)", match.group(1))
                        }
            if message.get("role") == "assistant":
                usage = record.get("usage", {}) or {}
                stats["cost_usd"] += float(usage.get("costUsd", 0.0) or 0.0)
                stats["input_tokens"] += int(usage.get("inputTokens", 0) or 0)
                stats["output_tokens"] += int(usage.get("outputTokens", 0) or 0)
                stats["cache_read_tokens"] += int(usage.get("cacheReadTokens", 0) or 0)
                stats["cache_write_tokens"] += int(usage.get("cacheWriteTokens", 0) or 0)
                stats["peak_input_tokens"] = max(
                    stats["peak_input_tokens"], int(usage.get("inputTokens", 0) or 0)
                )
                if record.get("model"):
                    stats["models"].add(record["model"])
    return stats


def run_git(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=15, check=False,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def agent_model_pin(repo: Path, agent_type: str) -> str:
    candidate = repo / "agents" / f"{agent_type}.md"
    if not candidate.exists():
        return "no agent file (built-in or uninstalled)"
    match = re.search(r"^model:\s*(.+)$", candidate.read_text(), re.MULTILINE)
    return match.group(1).strip() if match else "inherit"


def evidence_inventory(run_dir: Path) -> list[dict]:
    evidence_dir = run_dir / "EVIDENCE"
    if not evidence_dir.is_dir():
        return []
    files = [
        {"name": item.name, "bytes": item.stat().st_size}
        for item in evidence_dir.iterdir() if item.is_file()
    ]
    return sorted(files, key=lambda item: item["name"])


def usage_summary(usage: dict) -> str:
    if not usage:
        return "usage not reported in the tool result"
    return (
        f"{usage.get('total_tokens', '?')} tokens · {usage.get('turns', '?')} turns · "
        f"{usage.get('duration_ms', '?')} ms"
    )


def render(receipt: dict) -> str:
    frontmatter = receipt["frontmatter"]
    stats = receipt["stats"]
    out: list[str] = []
    add = out.append
    add(f"# RECEIPT — {receipt['run_id']}")
    add("")
    add(f"Generated {receipt['generated_at']} by tools/run_receipt.py from TASK.md, the session")
    add("transcript, EVIDENCE/, and git. **Authored** facts are quoted from TASK.md; everything")
    add("else is derived. The receipt interprets nothing and stores nothing.")
    add("")
    add("## Identity")
    add("")
    add(f"- Session: `{receipt['session_path'] or UNKNOWN}`")
    add(f"- Repo: `{receipt['repo']}` · HEAD `{receipt['head'] or UNKNOWN}`")
    add(f"- Transcript: {stats['records']} records · {stats['messages']} messages · "
        f"{stats['parse_errors']} unparseable lines")
    add(f"- Run agents (authored): {fmt(field(frontmatter, 'agents'))}")
    add("")
    add("## Objective and criterion (authored)")
    add("")
    add(f"- Request: {fmt(field(frontmatter, 'request'))}")
    add(f"- Criterion: {fmt(field(frontmatter, 'criterion'))}")
    add("")
    add("## Verdicts and override (authored; ruled by human)")
    add("")
    verdicts = field(frontmatter, "verdicts")
    if not isinstance(verdicts, list) or not verdicts:
        add(f"- No verdict recorded. The receipt reports this; nothing blocks the turn (Phase 2 D-R1).")
    else:
        for entry in verdicts:
            if not isinstance(entry, dict):
                continue
            add(f"- **{entry.get('claim')}** — {entry.get('verdict')} ({entry.get('by', '')})")
            if entry.get("evidence"):
                add(f"  - Evidence: {entry.get('evidence')}")
            if entry.get("qualification"):
                add(f"  - Qualification: {entry.get('qualification')}")
        add("")
        override = field(frontmatter, "override")
        add(f"- Override: {fmt(override) if override not in (None, 'null') else 'none recorded'}")
    add("")
    add("## Evidence bundle (derived)")
    add("")
    if receipt["evidence"]:
        add(f"{len(receipt['evidence'])} file(s) under EVIDENCE/:")
        for item in receipt["evidence"]:
            add(f"- `EVIDENCE/{item['name']}` ({item['bytes']} bytes)")
    else:
        add("- EVIDENCE/ is empty or missing.")
    add("")
    add("## Session facts (derived from the transcript)")
    add("")
    add(f"- Human messages (meta.source user|steering): {stats['human_msgs']} of {stats['messages']}")
    add(f"- Tool results: {stats['tool_results']}")
    add(f"- Models on assistant records: {', '.join(sorted(stats['models'])) or UNKNOWN}")
    add(f"- Cost (sum usage.costUsd, main session only): ${stats['cost_usd']:.4f}")
    cache_share = (stats["cache_read_tokens"] / stats["input_tokens"] * 100.0) if stats["input_tokens"] else 0.0
    add(f"- Input tokens {stats['input_tokens']} (inclusive of cache-read; verified against cost "
        f"arithmetic) · output {stats['output_tokens']} · cache-read {stats['cache_read_tokens']} "
        f"({cache_share:.1f}% of input)")
    add(f"- Peak assistant input tokens (context proxy): {stats['peak_input_tokens']}")
    add(f"- Window: {stats['first_ts'] or UNKNOWN} → {stats['last_ts'] or UNKNOWN}")
    add("")
    add("## Delegations (derived; subagent internals are not captured)")
    add("")
    if stats["agents"]:
        for agent in stats["agents"]:
            pin = receipt["pins"].get(agent["type"], "unknown")
            add(f"- `{agent['type']}` — {agent['description']}")
            add(f"  - Model pin: {pin} · honored: {UNKNOWN} (transcript records no subagent model)")
            add(f"  - Tool-result usage: {usage_summary(agent['usage'])}")
        add("")
        add("- Subagent cost is not in `usage.costUsd`; only the main session's cost is summed.")
    else:
        add("- None recorded.")
    add("")
    add("## Files this run wrote in the repo (derived from git status)")
    add("")
    add("```")
    add(receipt["git_status"] or "(clean)")
    add("```")
    add("")
    add(f"- Base state (authored): {fmt(field(frontmatter, 'base_state'))}")
    add(f"- Result state (authored): {fmt(field(frontmatter, 'result_state'))}")
    add("")
    add("## Skills (authored vs observable)")
    add("")
    add(f"- Intended (authored): {fmt(field(frontmatter, 'skills.intended'))}")
    add(f"- Actually activated: {UNKNOWN} — the harness does not record skill activation.")
    add("")
    add("## Gaps")
    add("")
    if receipt["gaps"]:
        for gap in receipt["gaps"]:
            add(f"- {gap}")
    else:
        add("- None detected.")
    add("")
    add("## Continue here")
    add("")
    add(f"- Run directory: `{receipt['run_dir']}`")
    add("- Read in this order: TASK.md (authored intent) → EVIDENCE/ (raw world) → "
        "LEDGER.md (claim verdicts) → REVIEW.md (independent review) → TASK.md verdicts (human ruling).")
    rollback = field(frontmatter, "rollback_tested")
    add(f"- Rollback: {fmt(rollback) if rollback not in (None, 'null') else 'not recorded — treat as unresolved'}")
    add("")
    return "\n".join(out)


def collect_gaps(frontmatter: dict, stats: dict, evidence: list[dict], session_arg) -> list[str]:
    gaps = []
    if not frontmatter:
        gaps.append("TASK.md frontmatter could not be parsed.")
    if field(frontmatter, "criterion") in (None, ""):
        gaps.append("No criterion authored — the run has no falsifiable acceptance test.")
    verdicts = field(frontmatter, "verdicts")
    if not isinstance(verdicts, list) or not verdicts:
        gaps.append("No verdict recorded yet — the run is not closed.")
    names = {item["name"] for item in evidence}
    for entry in verdicts or []:
        if not isinstance(entry, dict) or not entry.get("evidence"):
            continue
        for token in re.split(r"[,\s]+", str(entry["evidence"])):
            token = token.strip("`'\"")
            if token.startswith("EVIDENCE/") and Path(token).name not in names:
                gaps.append(f"Verdict for {entry.get('claim')} cites missing file {token}.")
    if stats["agents"]:
        gaps.append(
            f"Delegations vs artifacts: {len(stats['agents'])} agent call(s); EVIDENCE/ holds "
            f"{len(evidence) or 'no'} file(s). Attribution of files to agents is {UNKNOWN}."
        )
    if not session_arg or not Path(session_arg).exists():
        gaps.append(f"Transcript not read: {session_arg or 'no --session given'}.")
    if field(frontmatter, "result_state") in (None, "null"):
        gaps.append("result_state not set — the run's end state is not recorded.")
    if field(frontmatter, "rollback_tested") in (None, "null"):
        gaps.append("rollback_tested not set.")
    return gaps


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a run receipt (read-only).")
    parser.add_argument("--session", type=Path, default=None)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    run_dir = args.run.resolve()
    task_path = run_dir / "TASK.md"
    if not task_path.exists():
        print(f"error: {task_path} not found", file=sys.stderr)
        return 2
    frontmatter = parse_frontmatter(task_path.read_text())
    repo = run_dir.parent.parent
    stats = read_transcript(args.session)
    evidence = evidence_inventory(run_dir)
    pins = {agent["type"]: agent_model_pin(repo, agent["type"]) for agent in stats["agents"]}

    receipt = {
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "session_path": str(args.session) if args.session else None,
        "repo": str(repo),
        "head": run_git(repo, "rev-parse", "HEAD"),
        "git_status": run_git(repo, "status", "--porcelain"),
        "frontmatter": frontmatter,
        "evidence": evidence,
        "stats": stats,
        "pins": pins,
        "gaps": collect_gaps(frontmatter, stats, evidence, args.session),
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    output_path = args.out or (run_dir / "RECEIPT.md")
    output_path.write_text(render(receipt))
    print(f"wrote {output_path} ({len(receipt['gaps'])} gap(s) reported)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
