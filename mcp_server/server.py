"""Stateless, read-only MCP surface over this repository's skills/ and runs/.

Serves no procedure text of its own. Prompts are read from `skills/*/SKILL.md` at
request time, so moving `skills/` aside makes `prompts/list` return nothing. That
property is the reason this server can exist without becoming a second copy of the
procedure.

Read-only by construction: there is no write path. `tools/run_receipt.py` remains a
script a human runs.

Optional dependency. Install with `uv sync --extra mcp`; run with
`uv run --extra mcp python mcp_server/server.py`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

REPO = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO / "skills"
RUNS_DIR = REPO / "runs"

sys.path.insert(0, str(REPO / "tools"))
import run_receipt  # noqa: E402

mcp = MCPServer(
    name="run-discipline",
    version="0.0.1",
    instructions=(
        "The engineering-run procedure: a falsifiable criterion authored before work, "
        "raw command output retained as evidence, an independent review, and a recorded "
        "human ruling. Prompts are the six procedures and are read from skills/ at request "
        "time; the tools are read-only checks over a run directory. Nothing here writes."
    ),
)


def _body_after_frontmatter(text: str) -> str:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1:]).lstrip("\n")
    return text


def load_skills() -> list[dict]:
    if not SKILLS_DIR.is_dir():
        return []
    skills = []
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        frontmatter = run_receipt.parse_frontmatter(text)
        fallback = path.parent.name
        skills.append(
            {
                "name": str(run_receipt.field(frontmatter, "name") or fallback).strip(),
                "description": str(
                    run_receipt.field(frontmatter, "description")
                    or f"Procedure: {fallback}"
                ).strip(),
                "body": _body_after_frontmatter(text),
                "references": sorted(
                    item for item in (path.parent / "references").glob("*")
                    if item.is_file()
                ),
                "path": path,
            }
        )
    return skills


def resolve_run(name: str) -> Path:
    candidate = (RUNS_DIR / name).resolve()
    root = RUNS_DIR.resolve()
    if not candidate.is_dir() or root not in candidate.parents:
        raise ValueError(f"not a run directory under runs/: {name!r}")
    return candidate


def read_task(run_dir: Path) -> dict:
    task = run_dir / "TASK.md"
    if not task.exists():
        raise ValueError(f"{run_dir.name}: TASK.md not found")
    return run_receipt.parse_frontmatter(task.read_text(encoding="utf-8"))


def transcript_path(frontmatter: dict) -> Path | None:
    raw = run_receipt.field(frontmatter, "session_file")
    if not raw:
        return None
    candidate = Path(str(raw)).expanduser()
    return candidate if candidate.is_absolute() else (REPO / candidate)


def _register(skill: dict) -> None:
    def handler() -> str:
        return skill["body"]

    handler.__doc__ = skill["description"]
    mcp.prompt(name=skill["name"], description=skill["description"])(handler)


def _make_reader(path: Path, skill_name: str):
    def reader() -> str:
        return path.read_text(encoding="utf-8")

    reader.__doc__ = f"Reference for the {skill_name} procedure."
    return reader


for _skill in load_skills():
    _register(_skill)
    for _reference in _skill["references"]:
        mcp.resource(
            f"skill://{_skill['name']}/references/{_reference.name}",
            name=_reference.name,
            mime_type="text/markdown",
        )(_make_reader(_reference, _skill["name"]))


@mcp.tool()
def list_runs() -> str:
    """List every run directory under runs/ with its tier and completion state."""
    if not RUNS_DIR.is_dir():
        return json.dumps([])
    rows = []
    for entry in sorted(RUNS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        try:
            frontmatter = read_task(entry)
        except ValueError as error:
            rows.append({"run": entry.name, "error": str(error)})
            continue
        verdicts = run_receipt.field(frontmatter, "verdicts")
        rows.append(
            {
                "run": entry.name,
                "tier": run_receipt.field(frontmatter, "tier") or "unset",
                "criterion": bool(run_receipt.field(frontmatter, "criterion")),
                "verdicts": len(verdicts) if isinstance(verdicts, list) else 0,
                "evidence_files": len(run_receipt.evidence_inventory(entry)),
                "override_recorded": run_receipt.field(frontmatter, "override")
                not in (None, "null"),
            }
        )
    return json.dumps(rows, indent=2, default=str)


@mcp.tool()
def check_run(run: str) -> str:
    """Return the gap list for a run: what it failed to record. Read-only.

    Args:
        run: The run directory name under runs/, e.g. 2026-09-12-f9-f10-readjudication.
    """
    run_dir = resolve_run(run)
    frontmatter = read_task(run_dir)
    session = transcript_path(frontmatter)
    stats = run_receipt.read_transcript(session)
    evidence = run_receipt.evidence_inventory(run_dir)
    gaps = run_receipt.collect_gaps(frontmatter, stats, evidence, session)
    return json.dumps(
        {"run": run_dir.name, "gap_count": len(gaps), "gaps": gaps}, indent=2
    )


@mcp.tool()
def hash_evidence(run: str) -> str:
    """Return the sha256 of every file in a run's EVIDENCE/ directory. Read-only.

    Byte sizes detect truncation; hashes detect substitution.

    Args:
        run: The run directory name under runs/.
    """
    run_dir = resolve_run(run)
    evidence_dir = run_dir / "EVIDENCE"
    digests = {}
    if evidence_dir.is_dir():
        for item in sorted(evidence_dir.iterdir()):
            if item.is_file():
                digests[item.name] = hashlib.sha256(item.read_bytes()).hexdigest()
    return json.dumps({"run": run_dir.name, "files": digests}, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
