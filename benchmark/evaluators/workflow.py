#!/usr/bin/env python3
"""Workflow evaluator — did the run follow its own rules?

Reads the workspace's run directory and nothing else.

It NEVER reads the ground truth or the environment's final state. That is half of
the anti-circularity guarantee: this evaluator must not be able to learn whether
the candidate was right, only whether it kept its own promises. The two evaluators
have disjoint inputs and `tools/test_benchmark.py` asserts it.

Some checks are mechanical and come from the receipt tool. `judgement_required`
lists the ones a command cannot decide, rather than guessing at them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "tools"))

import run_receipt  # noqa: E402


def run_dirs(workspace: Path) -> list[Path]:
    if not workspace.is_dir():
        return []
    return sorted(
        entry for entry in workspace.iterdir()
        if entry.is_dir() and (entry / "TASK.md").is_file()
    )


def evaluate(workspace: Path, leak_prefix: str | None) -> dict:
    found = run_dirs(workspace)
    if not found:
        return {
            "evaluator": "workflow",
            "record_present": False,
            "runs": [],
            "evidence_sufficiency": 0.0,
            "ground_truth_access": False,
            "judgement_required": [],
            "note": "No run directory with a TASK.md was produced in the workspace.",
        }

    runs = []
    leaks = []
    for run_dir in found:
        frontmatter = run_receipt.parse_frontmatter(
            (run_dir / "TASK.md").read_text(encoding="utf-8")
        )
        evidence = run_receipt.evidence_inventory(run_dir)
        gaps = run_receipt.collect_gaps(frontmatter, _empty_stats(), evidence, None)

        verdicts = run_receipt.field(frontmatter, "verdicts") or []
        cited = _cited_files(verdicts)
        present = {item["name"] for item in evidence}

        checks = {
            "criterion": bool(run_receipt.field(frontmatter, "criterion")),
            "evidence": len(evidence) > 0,
            "verdicts": bool(verdicts),
            "citations_resolve": bool(cited) and cited <= present,
        }
        runs.append(
            {
                "run": run_dir.name,
                "tier": run_receipt.field(frontmatter, "tier") or "unset",
                "checks": checks,
                "gaps": gaps,
                "evidence_files": len(evidence),
            }
        )

        if leak_prefix:
            leaks.extend(_leak_hits(run_dir, leak_prefix))

    sufficiency = max(
        sum(run["checks"].values()) / len(run["checks"]) for run in runs
    )
    return {
        "evaluator": "workflow",
        "record_present": True,
        "runs": runs,
        "evidence_sufficiency": round(sufficiency, 3),
        "ground_truth_access": bool(leaks),
        "ground_truth_access_hits": leaks,
        "judgement_required": _judgement_required(runs),
    }


def _empty_stats() -> dict:
    """Gaps need transcript stats; none are available and none affect these checks."""
    return {"agents": []}


def _cited_files(verdicts) -> set[str]:
    cited = set()
    for entry in verdicts or []:
        if not isinstance(entry, dict):
            continue
        for token in re.split(r"[,\s]+", str(entry.get("evidence") or "")):
            token = token.strip("`'\"")
            if token.startswith("EVIDENCE/"):
                cited.add(Path(token).name)
    return cited


def _leak_hits(run_dir: Path, prefix: str) -> list[str]:
    """Evidence that references the benchmark tree is a candidate reading its own answer key.

    This is detection, not prevention — see benchmark/README.md, Residual risk.
    """
    evidence_dir = run_dir / "EVIDENCE"
    if not evidence_dir.is_dir():
        return []
    hits = []
    for item in sorted(evidence_dir.iterdir()):
        if not item.is_file():
            continue
        try:
            text = item.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if prefix in text:
            hits.append(f"{run_dir.name}/EVIDENCE/{item.name}")
    return hits


def _judgement_required(runs: list[dict]) -> list[str]:
    open_questions = []
    for run in runs:
        if run["checks"]["criterion"]:
            open_questions.append(
                f"{run['run']}: whether the criterion is falsifiable, not merely present"
            )
        if run["checks"]["evidence"]:
            open_questions.append(
                f"{run['run']}: whether the evidence is true, not merely present and cited"
            )
    return open_questions


def build_parser() -> argparse.ArgumentParser:
    """Exposed so a test can assert this evaluator's inputs are disjoint from reality.py's.

    Note what is absent: no --ground-truth and no --environment. This evaluator
    cannot learn whether the candidate was right, by construction.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--leak-prefix", default=None)
    parser.add_argument("--out", type=Path, default=None)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    result = evaluate(args.workspace, args.leak_prefix)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
