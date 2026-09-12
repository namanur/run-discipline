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

import functools
import hashlib
import json
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

REPO = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO / "skills"
RUNS_DIR = REPO / "runs"
BENCHMARK_DIR = REPO / "benchmark"
TESTS_DIR = BENCHMARK_DIR / "tests"
RESULTS_DIR = BENCHMARK_DIR / "results"

sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(BENCHMARK_DIR / "evaluators"))
import run_receipt  # noqa: E402
import reality  # noqa: E402

mcp = MCPServer(
    name="run-discipline",
    version="0.0.2",
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


def safe(fn):
    """Turn a bad argument into a message the caller can act on.

    Without this the SDK wraps the ValueError into "Error executing tool name" and the
    actual reason never reaches the model. Raising is correct protocol behaviour;
    losing the message is not.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as exc:
            return json.dumps({"error": str(exc)}, indent=2)

    return wrapper


@mcp.tool()
@safe
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
@safe
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
@safe
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


def load_yaml(path: Path) -> dict:
    return run_receipt.parse_frontmatter("---\n" + path.read_text(encoding="utf-8") + "---\n")


def resolve_test(test: str) -> Path:
    spec = (TESTS_DIR / test).resolve()
    if not spec.is_dir() or TESTS_DIR.resolve() not in spec.parents:
        raise ValueError(f"not a benchmark test: {test!r}")
    if not (spec / "test.yaml").is_file():
        raise ValueError(f"{test}: no test.yaml")
    return spec


def resolve_result(suite: str, test: str, mode: str) -> Path:
    path = (RESULTS_DIR / suite / f"{test}-{mode}" / "result.json").resolve()
    root = RESULTS_DIR.resolve()
    if root not in path.parents or not path.is_file():
        raise ValueError(f"no stored result at {suite}/{test}-{mode}")
    return path


@mcp.tool()
@safe
def list_tests() -> str:
    """List every benchmark test with its category, status and objective. Read-only."""
    if not TESTS_DIR.is_dir():
        return json.dumps([])
    rows = []
    for path in sorted(TESTS_DIR.glob("*/test.yaml")):
        spec = load_yaml(path)
        rows.append(
            {
                "id": spec.get("id", path.parent.name),
                "name": spec.get("name"),
                "category": spec.get("category"),
                "status": spec.get("status"),
                "risk": spec.get("risk"),
                "environment": spec.get("environment"),
                "modes": spec.get("modes"),
            }
        )
    return json.dumps(rows, indent=2, default=str)


@mcp.tool()
@safe
def get_test(test_id: str) -> str:
    """Return one benchmark test: its specification and, if built, its ground truth. Read-only.

    The ground truth is included deliberately — this server is for reading and auditing
    results, not for running candidates. A candidate must never be given this tool.

    Args:
        test_id: e.g. FP-001
    """
    path = resolve_test(test_id)
    spec = load_yaml(path / "test.yaml")
    payload = {"test": spec}
    truth_path = BENCHMARK_DIR / "ground-truth" / f"{test_id}.yaml"
    if truth_path.is_file():
        payload["ground_truth"] = load_yaml(truth_path)
    return json.dumps(payload, indent=2, default=str)


@mcp.tool()
@safe
def get_result(suite: str, test: str, mode: str) -> str:
    """Return one stored result, with both evaluator outputs intact. Read-only.

    Args:
        suite: the suite id, e.g. 2026-01-09-first
        test: e.g. BASIC-001
        mode: baseline | minimal | candidate
    """
    return resolve_result(suite, test, mode).read_text(encoding="utf-8")


@mcp.tool()
@safe
def validate_result(suite: str, test: str, mode: str) -> str:
    """Check a stored result against the documented contract. Read-only.

    Args:
        suite: the suite id
        test: e.g. BASIC-001
        mode: baseline | minimal | candidate
    """
    result = json.loads(resolve_result(suite, test, mode).read_text(encoding="utf-8"))
    problems = []
    for key in ("suite", "test", "mode", "status", "reality", "workflow", "measurements"):
        if key not in result:
            problems.append(f"missing key: {key}")
    if result.get("status") not in ("complete", "budget_exceeded", "harness_error", "evaluator_error"):
        problems.append(f"unknown status: {result.get('status')}")
    if result.get("status") == "complete":
        if not isinstance(result.get("reality"), dict):
            problems.append("reality must be an object, not a merged score")
        if not isinstance(result.get("workflow"), dict):
            problems.append("workflow must be an object, not a merged score")
        if result.get("reality", {}).get("outcome") not in (
            "correct", "acceptable", "incorrect", "forbidden", "unnecessary_unknown", "missing",
        ):
            problems.append(f"unknown reality outcome: {result.get('reality', {}).get('outcome')}")
    if "inputs" not in result:
        problems.append("missing inputs — this result cannot be replayed")
    return json.dumps(
        {"suite": suite, "test": test, "mode": mode, "valid": not problems, "problems": problems},
        indent=2,
    )


@mcp.tool()
@safe
def compare_runs(suite_a: str, suite_b: str | None = None) -> str:
    """Compare suites per mode, or compare modes within one suite. Read-only.

    With one argument, compares the three arms inside `suite_a` — the comparison that
    carries the result. With two, compares two suites mode by mode.

    Args:
        suite_a: a suite id under benchmark/results/
        suite_b: optional second suite id
    """
    def summarise(suite):
        rows = {}
        directory = RESULTS_DIR / suite
        if not directory.is_dir():
            raise ValueError(f"no such suite: {suite!r}")
        for path in sorted(directory.glob("*/result.json")):
            result = json.loads(path.read_text(encoding="utf-8"))
            row = rows.setdefault(
                result["mode"],
                {"scored": 0, "correct": 0, "forbidden": 0, "unnecessary_unknown": 0, "record": 0},
            )
            if result.get("status") != "complete":
                continue
            row["scored"] += 1
            outcome = result["reality"]["outcome"]
            row["correct"] += 1 if outcome == "correct" else 0
            row["forbidden"] += 1 if outcome == "forbidden" else 0
            row["unnecessary_unknown"] += 1 if outcome == "unnecessary_unknown" else 0
            row["record"] += 1 if result["workflow"].get("record_present") else 0
        return rows

    first = summarise(suite_a)
    if suite_b is None:
        return json.dumps({"suite": suite_a, "by_mode": first}, indent=2, sort_keys=True)
    second = summarise(suite_b)
    deltas = {}
    for mode in sorted(set(first) | set(second)):
        a = first.get(mode, {})
        b = second.get(mode, {})
        deltas[mode] = {
            key: (b.get(key, 0) - a.get(key, 0))
            for key in ("scored", "correct", "forbidden", "unnecessary_unknown", "record")
        }
    return json.dumps(
        {"a": {"suite": suite_a, "by_mode": first}, "b": {"suite": suite_b, "by_mode": second},
         "delta_b_minus_a": deltas},
        indent=2, sort_keys=True,
    )


@mcp.tool()
@safe
def replay_test(suite: str, test: str, mode: str) -> str:
    """Re-derive a stored result's reality verdict from its stored inputs. Read-only.

    Detects an evaluator that has changed its mind since the run. The workflow half
    is **not** replayable — the workspace it read was discarded — and this reports
    that as UNKNOWN rather than guessing.

    Args:
        suite: the suite id
        test: e.g. BASIC-001
        mode: baseline | minimal | candidate
    """
    result = json.loads(resolve_result(suite, test, mode).read_text(encoding="utf-8"))
    truth_path = BENCHMARK_DIR / "ground-truth" / f"{test}.yaml"
    if not truth_path.is_file():
        raise ValueError(f"{test}: no ground truth to replay against")
    ground_truth = load_yaml(truth_path)
    inputs = result.get("inputs") or {}
    claim = reality.parse_claim(inputs.get("answer") or "")
    outcome = reality.classify(claim, ground_truth.get("expected") or {})
    mismatches = reality.compare_states(
        ground_truth.get("environment_final_state") or {},
        inputs.get("environment_reality") or {},
    )
    stored = (result.get("reality") or {}).get("outcome")
    return json.dumps(
        {
            "suite": suite,
            "test": test,
            "mode": mode,
            "stored_outcome": stored,
            "replayed_outcome": outcome,
            "agrees": stored == outcome,
            "fixture_drifted": bool(mismatches),
            "mismatches": mismatches,
            "workflow": "UNKNOWN — not replayable; the workspace was discarded",
        },
        indent=2, sort_keys=True,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
