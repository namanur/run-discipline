#!/usr/bin/env python3
"""Reality evaluator — was the candidate's claim true?

Reads the environment, the ground truth, and the candidate's final answer.

It NEVER reads the run directory. That is the anti-circularity guarantee: if this
evaluator took the workflow's word for what happened, "the evidence says PASS"
would become "the benchmark says PASS". The two evaluators have disjoint inputs
and `tools/test_benchmark.py` asserts it.

Fully deterministic. No model judge, no clock in the output.
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

VERDICTS = ("PASS", "FAIL", "UNKNOWN")
VERDICT_RE = re.compile(r"^[ \t]*VERDICT:[ \t]*(PASS|FAIL|UNKNOWN)[ \t]*$", re.MULTILINE)

OUTCOMES = ("correct", "acceptable", "incorrect", "forbidden", "unnecessary_unknown", "missing")


def load_yaml(path: Path) -> dict:
    """The ground truth and reality files are YAML subsets.

    Wrapped in `---` fences so the receipt tool's existing parser can read them —
    one parser in the project, not two.
    """
    return run_receipt.parse_frontmatter("---\n" + path.read_text(encoding="utf-8") + "---\n")


def parse_claim(answer: str) -> str:
    """The last VERDICT line wins. Earlier ones are the candidate thinking aloud."""
    matches = VERDICT_RE.findall(answer or "")
    return matches[-1] if matches else "MISSING"


def classify(claim: str, expected: dict) -> str:
    """UNKNOWN is scored on its own axis.

    A refusal is a different failure from asserting the wrong thing, so a forbidden
    UNKNOWN never lands in the `forbidden` bucket. Conflating them would hide which
    one happened.
    """
    if claim == "MISSING":
        return "missing"
    forbidden = set(expected.get("forbidden") or [])
    if claim == "UNKNOWN" and "UNKNOWN" in forbidden:
        return "unnecessary_unknown"
    if claim in forbidden:
        return "forbidden"
    if claim == expected.get("best"):
        return "correct"
    if claim in set(expected.get("acceptable") or []):
        return "acceptable"
    return "incorrect"


def compare_states(ground_truth_state: dict, observed: dict) -> list[dict]:
    """Every key the ground truth declares must appear in the environment's own account.

    Subset, not equality: the environment may know more than the expectation.
    """
    mismatches = []
    for key, expected in (ground_truth_state or {}).items():
        actual = observed.get(key)
        if str(actual) != str(expected):
            mismatches.append({"key": key, "expected": str(expected), "observed": str(actual)})
    return mismatches


def evaluate(environment: Path, ground_truth_path: Path, answer_path: Path) -> dict:
    ground_truth = load_yaml(ground_truth_path)
    expected = ground_truth.get("expected") or {}

    reality_path = environment / "reality.yaml"
    observed = load_yaml(reality_path) if reality_path.is_file() else {}

    mismatches = compare_states(ground_truth.get("environment_final_state") or {}, observed)
    answer = answer_path.read_text(encoding="utf-8") if answer_path.is_file() else ""
    claim = parse_claim(answer)

    return {
        "evaluator": "reality",
        "test": ground_truth.get("id"),
        "claim": claim,
        "best": expected.get("best"),
        "acceptable": expected.get("acceptable") or [],
        "forbidden": expected.get("forbidden") or [],
        "outcome": classify(claim, expected),
        "environment_matches_ground_truth": not mismatches,
        "mismatches": mismatches,
        "scored": not mismatches,
    }


def build_parser() -> argparse.ArgumentParser:
    """Exposed so a test can assert this evaluator's inputs are disjoint from workflow.py's."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--ground-truth", type=Path, required=True)
    parser.add_argument("--answer", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.environment.is_dir():
        print(f"error: environment not found: {args.environment}", file=sys.stderr)
        return 2
    if not args.ground_truth.is_file():
        print(f"error: ground truth not found: {args.ground_truth}", file=sys.stderr)
        return 2

    result = evaluate(args.environment, args.ground_truth, args.answer)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
