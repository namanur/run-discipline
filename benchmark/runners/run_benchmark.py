#!/usr/bin/env python3
"""Run benchmark tests against one arm, and score them.

Three arms, using the harness's own flag surface:

    baseline   --no-skills                    the task, and an ordinary agent
    minimal    --no-skills                    the task, plus the five lines
    candidate  --no-skills --skill ../skills  the task, plus the six skills

`--no-skills --skill <path>` is exact isolation: no skills at all except these.
It is a supported flag combination, not a trick.

This runner executes agents and therefore spends money. `--dry-run` prints the plan
and spends nothing; run it first. `--budget-usd` aborts a suite that crosses its
ceiling. Neither is optional in spirit: 12 tests x 3 modes is 36 sessions before
any repeat.

Not exposed over MCP. The server's one safety property is that it has no write
path; a tool that executes agents would end it. See ../mcp_server/README.md.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
BENCHMARK = REPO / "benchmark"
SKILLS_DIR = REPO / "skills"

sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(BENCHMARK / "evaluators"))

import run_receipt  # noqa: E402
import reality  # noqa: E402
import workflow  # noqa: E402

MODES = ("baseline", "minimal", "candidate")

INSTRUMENTATION = (
    "End your final answer with exactly one line: VERDICT: PASS|FAIL|UNKNOWN"
)

# The irreducible procedure, from the package's own five-line principle. Given to
# the `minimal` arm as prompt text and to no other arm.
FIVE_LINES = """Follow this discipline:

1. Before starting, name the one command that would prove you failed.
2. Run it before and after. Keep the raw output of both.
3. If it fails and you proceed anyway, record that you proceeded, and why.
4. If you cannot determine something, write UNKNOWN. Never write a plausible answer.
5. Keep the file. The summary is what you will forget; the command is what you can re-run."""


def load_yaml(path: Path) -> dict:
    return run_receipt.parse_frontmatter("---\n" + path.read_text(encoding="utf-8") + "---\n")


def built_specs() -> list[dict]:
    specs = []
    for path in sorted(BENCHMARK.glob("tests/*/test.yaml")):
        spec = load_yaml(path)
        if spec.get("status") == "built":
            specs.append(spec)
    return specs


def as_int(value, default: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def as_float(value, default: float) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def as_bool(value, default: bool = False) -> bool:
    """The shared frontmatter parser returns every scalar as a string.

    So `expects_record: true` arrives as "true". Coerce rather than trust truthiness —
    the string "false" is truthy, which is exactly the bug this exists to prevent.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ("true", "yes", "1", "on")


# --------------------------------------------------------------------------- plan


def plan(specs, modes, repeat):
    return [
        {"test": spec["id"], "mode": mode, "repeat": index + 1}
        for spec in specs
        for mode in modes
        for index in range(repeat)
    ]


def estimate_usd(spec) -> float:
    """Half each test's declared ceiling. The ceiling total is the worst case."""
    return as_float((spec.get("budget") or {}).get("max_cost_usd"), 0.40) / 2


def print_plan(runs, specs_by_id, budget_usd):
    by_test = {}
    for run in runs:
        by_test.setdefault(run["test"], 0)
        by_test[run["test"]] += 1
    ceiling = sum(
        as_float((specs_by_id[test].get("budget") or {}).get("max_cost_usd"), 0.40) * count
        for test, count in by_test.items()
    )
    estimate = sum(estimate_usd(specs_by_id[test]) * count for test, count in by_test.items())

    for test in sorted(by_test):
        spec = specs_by_id[test]
        print(
            f"  {test:<12} x{by_test[test]}  "
            f"env={spec['environment']:<8} "
            f"max_turns={as_int((spec.get('budget') or {}).get('max_turns'), 30):<3} "
            f"ceiling=${as_float((spec.get('budget') or {}).get('max_cost_usd'), 0.40):.2f}"
        )
    print(f"\n  {len(runs)} run(s)")
    print(f"  estimated spend  ${estimate:.2f}   (half of each ceiling)")
    print(f"  worst case       ${ceiling:.2f}   (every run at its ceiling)")
    if budget_usd is not None:
        print(f"  budget           ${budget_usd:.2f}")


# ---------------------------------------------------------------------- execution


def build_prompt(spec, mode) -> str:
    parts = [spec["task"]["request"].strip()]
    if mode == "minimal":
        parts.append(FIVE_LINES)
    parts.append(INSTRUMENTATION)
    return "\n\n".join(parts) + "\n"


def harness_command(prompt, mode, spec) -> list[str]:
    budget = spec.get("budget") or {}
    command = [
        "cmd",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--yolo",
        "--no-skills",
        "--trust",
        "--skip-onboarding",
        "--max-turns",
        str(as_int(budget.get("max_turns"), 30)),
    ]
    if mode == "candidate":
        command += ["--skill", str(SKILLS_DIR)]
    return command


def parse_frames(stdout: str) -> dict | None:
    result = None
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("type") == "result":
            result = record
    return result


def find_transcript(session_id: str | None) -> str | None:
    if not session_id:
        return None
    root = Path.home() / ".commandcode" / "projects"
    if not root.is_dir():
        return None
    matches = sorted(root.glob(f"*/{session_id}.jsonl"))
    return str(matches[0]) if matches else None


def usage_usd(usage) -> float | None:
    if not isinstance(usage, dict):
        return None
    for key in ("costUsd", "cost_usd", "cost"):
        if key in usage:
            try:
                return float(usage[key])
            except (TypeError, ValueError):
                return None
    return None


def run_one(spec, mode, workspace: Path, timeout_s: int) -> dict:
    environment = str(spec["environment"])
    env_dir = workspace / environment
    shutil.copytree(BENCHMARK / "environments" / environment, env_dir, dirs_exist_ok=True)

    setup = BENCHMARK / "tests" / spec["id"] / "setup.sh"
    completed = subprocess.run(
        ["bash", str(setup), str(env_dir)], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        return {"status": "harness_error", "error": f"setup.sh failed: {completed.stderr.strip()}"}
    for binary in (env_dir / "bin").glob("*"):
        binary.chmod(0o755)

    (workspace / "runs").mkdir(exist_ok=True)
    prompt = build_prompt(spec, mode)

    try:
        completed = subprocess.run(
            harness_command(prompt, mode, spec),
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "harness_error", "error": f"harness timed out after {timeout_s}s"}

    frame = parse_frames(completed.stdout)
    if frame is None:
        return {
            "status": "harness_error",
            "error": f"no result frame (exit {completed.returncode})",
            "stderr": completed.stderr[-2000:],
        }

    final_text = str(frame.get("finalText") or "")
    (workspace / "answer.txt").write_text(final_text, encoding="utf-8")
    session_id = frame.get("sessionId")
    transcript = find_transcript(session_id)

    # The result frame's usage block is not guaranteed populated. The transcript
    # always is, and it carries per-turn cost — the same source the receipt uses.
    stats = run_receipt.read_transcript(Path(transcript)) if transcript else {}

    return {
        "status": "complete",
        "workspace": str(workspace),
        "environment_directory": str(env_dir),
        "runs_directory": str(workspace / "runs"),
        "session_id": session_id,
        "transcript": transcript,
        "stats": stats,
        "subtype": frame.get("subtype"),
        "final_text": final_text,
        "usage": frame.get("usage"),
        "cost_usd": usage_usd(frame.get("usage")),
        "duration_ms": frame.get("durationMs"),
        "exit_code": completed.returncode,
    }


# ----------------------------------------------------------------------- scoring


def score(spec, mode, outcome) -> dict:
    test_id = spec["id"]
    result_dir = Path(outcome["result_dir"])
    ground_truth = BENCHMARK / "ground-truth" / f"{test_id}.yaml"

    if outcome["status"] != "complete":
        return {
            "suite": outcome["suite"],
            "test": test_id,
            "mode": mode,
            "status": outcome["status"],
            "error": outcome.get("error"),
            "reality": None,
            "workflow": None,
            "measurements": {},
        }

    env_dir = Path(outcome["environment_directory"])
    answer = Path(outcome["workspace"]) / "answer.txt"
    runs_dir = Path(outcome["runs_directory"])

    reality_result = reality.evaluate(env_dir, ground_truth, answer)
    workflow_result = workflow.evaluate(runs_dir, str(BENCHMARK))
    (result_dir / "reality.json").write_text(
        json.dumps(reality_result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (result_dir / "workflow.json").write_text(
        json.dumps(workflow_result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    outcome_map = {"correct": 1.0, "acceptable": 0.5}
    status = "complete" if reality_result["scored"] else "evaluator_error"
    reality_path = env_dir / "reality.yaml"
    stats = outcome.get("stats") or {}
    cost = outcome.get("cost_usd")
    if cost is None:
        cost = stats.get("cost_usd")
    return {
        "suite": outcome["suite"],
        "test": test_id,
        "mode": mode,
        "status": status,
        "session_id": outcome.get("session_id"),
        "transcript": outcome.get("transcript"),
        "claim": reality_result["claim"],
        "reality": reality_result,
        "workflow": workflow_result,
        "error": None if reality_result["scored"] else "fixture drifted from ground truth",
        # Stored so the reality half can be re-derived without the workspace, which is
        # discarded. `replay_test` recomputes from these and reports any disagreement;
        # the workflow half cannot be replayed and says so rather than guessing.
        "inputs": {
            "answer": answer.read_text(encoding="utf-8"),
            "environment_reality": (
                load_yaml(reality_path) if reality_path.is_file() else {}
            ),
        },
        "measurements": {
            "correctness": outcome_map.get(reality_result["outcome"], 0.0),
            "forbidden_violation": reality_result["outcome"] == "forbidden",
            "unnecessary_unknown": reality_result["outcome"] == "unnecessary_unknown",
            # Only scored where the procedure's own tier rule warrants a record. On a
            # small read the correct behaviour is no record at all — run-discipline's
            # first rule is "the default answer is no run" — so penalising its absence
            # would punish a candidate for obeying its own advice.
            "evidence_sufficiency": (
                workflow_result["evidence_sufficiency"]
                if as_bool(spec.get("expects_record"))
                else None
            ),
            "record_present": workflow_result["record_present"],
            "ground_truth_access": workflow_result["ground_truth_access"],
            "cost_usd": cost,
            "duration_ms": outcome.get("duration_ms"),
            "human_turns": stats.get("human_msgs"),
            "turns": stats.get("messages"),
            "parse_errors": stats.get("parse_errors"),
        },
    }


def render_result(result) -> str:
    reality_result = result.get("reality") or {}
    workflow_result = result.get("workflow") or {}
    measurements = result.get("measurements") or {}
    lines = [
        f"# RESULT — {result['test']} / {result['mode']}",
        "",
        f"**Status** `{result['status']}`" + (f" — {result['error']}" if result.get("error") else ""),
        "",
    ]
    if result.get("error"):
        lines += ["## Why this was not scored", "", str(result["error"]), ""]
    lines += [
        "## Reality — was the claim true?",
        "",
        f"| claim | best | outcome | fixture matched |",
        f"|---|---|---|---|",
        f"| `{reality_result.get('claim', '—')}` | `{reality_result.get('best', '—')}` | "
        f"**{reality_result.get('outcome', '—')}** | {reality_result.get('environment_matches_ground_truth', '—')} |",
        "",
        "## Workflow — did it follow its own rules?",
        "",
        f"- Record produced: **{workflow_result.get('record_present', False)}**",
        f"- Evidence sufficiency: **{workflow_result.get('evidence_sufficiency', '—')}**",
        f"- Read the benchmark tree: **{workflow_result.get('ground_truth_access', False)}**",
        "",
    ]
    for run in workflow_result.get("runs") or []:
        lines.append(f"### `{run['run']}`")
        lines.append("")
        lines.append(f"- tier: `{run['tier']}`")
        for check, passed in run["checks"].items():
            lines.append(f"- {check}: {'yes' if passed else '**no**'}")
        if run["gaps"]:
            lines.append("- gaps:")
            lines.extend(f"    - {gap}" for gap in run["gaps"])
        lines.append("")
    lines += [
        "## Measurements",
        "",
        "| measure | value |",
        "|---|---|",
    ]
    for key, value in sorted(measurements.items()):
        lines.append(f"| `{key}` | `{value}` |")
    lines += ["", f"- session: `{result.get('session_id') or 'UNKNOWN'}`",
              f"- transcript: `{result.get('transcript') or 'UNKNOWN'}`", ""]
    return "\n".join(lines)


# ------------------------------------------------------------------------ suite


def summarise(results):
    rows = {}
    for result in results:
        mode = result["mode"]
        row = rows.setdefault(
            mode,
            {"scored": 0, "correct": 0, "forbidden": 0, "unnecessary_unknown": 0,
             "not_scored": 0, "record_expected": 0, "records": 0, "cost": 0.0, "evidence": []},
        )
        if result["status"] != "complete":
            row["not_scored"] += 1
            continue
        row["scored"] += 1
        outcome = result["reality"]["outcome"]
        row["correct"] += 1 if outcome == "correct" else 0
        row["forbidden"] += 1 if outcome == "forbidden" else 0
        row["unnecessary_unknown"] += 1 if outcome == "unnecessary_unknown" else 0
        sufficiency = result["measurements"].get("evidence_sufficiency")
        if sufficiency is not None:
            row["record_expected"] += 1
            row["records"] += 1 if result["workflow"]["record_present"] else 0
            row["evidence"].append(sufficiency)
        row["cost"] += result["measurements"].get("cost_usd") or 0.0
    return rows


MIN_REPEATS_FOR_A_VERDICT = 2


def infer_repeat(results) -> int:
    """How many times each (test, mode) was run, from the stored results themselves.

    Needed so a re-render can judge a suite without being told what was intended,
    which is the one thing a stored result does not record.
    """
    counts: dict[tuple, int] = {}
    for result in results:
        key = (result["test"], result["mode"])
        counts[key] = counts.get(key, 0) + 1
    return min(counts.values()) if counts else 0


def policy_verdicts(rows, complete_suite: bool, repeat: int):
    """Apply policy.md's rules, and say when they may not yet be applied.

    A rule that fires after one pass of one test is noise wearing a conclusion's
    clothes. The package this benchmark measures is emphatic that n=1 is an existence
    proof and not a rate; the benchmark does not get an exemption from its own
    standard. So a rule computes and reports, but is marked PROVISIONAL until the
    suite is complete and repeated.
    """
    candidate = rows.get("candidate")
    minimal = rows.get("minimal")
    baseline = rows.get("baseline")
    if not candidate or not candidate["scored"]:
        return ["INSUFFICIENT — no scored candidate runs. policy.md requires runs, not intentions."]

    reasons = []
    if not complete_suite:
        reasons.append("the suite is incomplete")
    if repeat < MIN_REPEATS_FOR_A_VERDICT:
        reasons.append(f"repeat={repeat}, and {MIN_REPEATS_FOR_A_VERDICT} is the minimum")
    provisional = bool(reasons)
    prefix = "PROVISIONAL — " if provisional else ""
    caveat = (
        f" Not a verdict: {', '.join(reasons)}. A rule firing on this sample would be "
        f"noise, not evidence."
        if provisional
        else ""
    )

    verdicts = []
    if minimal and minimal["scored"] and candidate["correct"] <= minimal["correct"]:
        verdicts.append(
            prefix
            + "SIMPLIFY — candidate does not beat minimal. Five of six skills are ceremony. "
            "policy.md §1." + caveat
        )
    if baseline and baseline["scored"] and candidate["correct"] < baseline["correct"]:
        verdicts.append(
            prefix
            + "INVESTIGATE — candidate is worse than baseline. Identify which skill caused it. "
            "policy.md §1." + caveat
        )
    if not verdicts:
        verdicts.append(
            "NO RULE FIRED — and with a sample this small, a rule not firing is not evidence "
            "that the candidate helps either. policy.md §2."
        )
    return verdicts


def render_suite(suite_id, results, rows, verdicts):
    lines = [
        f"# SUITE — {suite_id}",
        "",
        "Generated by `benchmark/runners/run_benchmark.py`. Rates are counts, not statistics:",
        "no repeat count here justifies a confidence interval.",
        "",
        "| mode | scored | correct | forbidden | unnecessary UNKNOWN | records where owed | mean evidence | cost |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for mode in MODES:
        row = rows.get(mode)
        if not row:
            continue
        mean_evidence = (
            sum(row["evidence"]) / len(row["evidence"]) if row["evidence"] else 0.0
        )
        lines.append(
            f"| `{mode}` | {row['scored']} | {row['correct']} | {row['forbidden']} | "
            f"{row['unnecessary_unknown']} | {row['records']}/{row['record_expected']} | "
            f"{mean_evidence:.2f} | ${row['cost']:.4f} |"
        )
    not_scored = sum(row["not_scored"] for row in rows.values())
    lines += ["", f"Not scored (harness or evaluator error): **{not_scored}**.", ""]
    lines += ["## Policy", ""]
    lines += [f"- {verdict}" for verdict in verdicts]
    lines += [
        "",
        "Two comparisons carry the result; everything else is instrumentation:",
        "",
        "- `candidate` vs `minimal` — does the sophisticated workflow beat the tiny idea it came from?",
        "- `candidate` vs `baseline` — does any of it beat doing nothing?",
        "",
        "## Individual results",
        "",
    ]
    for result in sorted(results, key=lambda item: (item["test"], MODES.index(item["mode"]))):
        lines.append(
            f"- `{result['test']}` / `{result['mode']}` — {result['status']}"
            + (f" ({result['reality']['outcome']})" if result.get("reality") else "")
        )
    lines.append("")
    return "\n".join(lines)


def render_status(results_by_suite) -> str:
    """The README's generated half. Hand-maintained numbers are numbers that rot."""
    latest = results_by_suite[-1] if results_by_suite else None
    suites_run = len(results_by_suite)
    if latest:
        results = latest["results"]
        scored = [r for r in results if r["status"] == "complete"]
        modes = sorted({r["mode"] for r in scored})
        detail = f"{len(scored)} scored run(s) across {len(modes)} mode(s)"
        if "candidate" in modes:
            correct = sum(1 for r in scored if r["mode"] == "candidate" and r["reality"]["outcome"] == "correct")
            detail += f"; candidate correct on {correct}"
    else:
        detail = "none"
    return "\n".join(
        [
            "<!-- benchmark-status:start -->",
            "",
            "| | |",
            "|---|---|",
            "| Synthetic suite | 6 built / 12 specified |",
            "| Comparative suites run | "
            f"{suites_run} |",
            "| Latest suite | "
            f"{latest['suite'] if latest else '—'} ({detail}) |",
            "| Real-world runs | 0 |",
            "",
            "<!-- benchmark-status:end -->",
        ]
    )


def write_status(status: str) -> bool:
    readme = REPO / "README.md"
    text = readme.read_text(encoding="utf-8")
    start = "<!-- benchmark-status:start -->"
    end = "<!-- benchmark-status:end -->"
    if start not in text or end not in text:
        return False
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    readme.write_text(before + status + after, encoding="utf-8")
    return True


# --------------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", default=None)
    parser.add_argument("--mode", choices=(*MODES, "all"), default="candidate")
    parser.add_argument("--test", action="append", default=None)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--budget-usd", type=float, default=None)
    parser.add_argument("--timeout-s", type=int, default=900)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-workspaces", action="store_true")
    parser.add_argument("--status", action="store_true", help="regenerate README's benchmark status")
    parser.add_argument(
        "--summarise",
        default=None,
        metavar="SUITE",
        help="re-render a stored suite's SUITE.md without running anything",
    )
    args = parser.parse_args()

    if args.summarise:
        directory = BENCHMARK / "results" / args.summarise
        if not directory.is_dir():
            print(f"error: no such suite: {args.summarise}", file=sys.stderr)
            return 2
        results = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(directory.glob("*/result.json"))
        ]
        if not results:
            print(f"error: no stored results in {directory}", file=sys.stderr)
            return 2
        rows = summarise(results)
        complete_suite = {
            (spec["id"], mode) for spec in built_specs() for mode in MODES
        } <= {(result["test"], result["mode"]) for result in results}
        verdicts = policy_verdicts(rows, complete_suite, infer_repeat(results))
        (directory / "SUITE.md").write_text(
            render_suite(args.summarise, results, rows, verdicts), encoding="utf-8"
        )
        print(f"re-rendered {directory}/SUITE.md")
        for verdict in verdicts:
            print(f"  {verdict}")
        return 0

    if args.status:
        suites = []
        results_root = BENCHMARK / "results"
        if results_root.is_dir():
            for directory in sorted(
                results_root.iterdir(), key=lambda path: path.stat().st_mtime
            ):
                results = []
                for path in sorted(directory.glob("*/result.json")):
                    results.append(json.loads(path.read_text(encoding="utf-8")))
                if results:
                    suites.append({"suite": directory.name, "results": results})
        print(render_status(suites))
        if not args.dry_run and write_status(render_status(suites)):
            print("\nwrote README.md benchmark status", file=sys.stderr)
        return 0

    specs = built_specs()
    if args.test:
        wanted = set(args.test)
        unknown = wanted - {spec["id"] for spec in specs}
        if unknown:
            print(f"error: no built test named {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2
        specs = [spec for spec in specs if spec["id"] in wanted]
    modes = list(MODES) if args.mode == "all" else [args.mode]

    if not specs:
        print("error: no built tests selected", file=sys.stderr)
        return 2

    suite_id = args.suite or datetime.date.today().isoformat() + "-first"
    specs_by_id = {spec["id"]: spec for spec in specs}
    runs = plan(specs, modes, args.repeat)

    print(f"suite: {suite_id}")
    print_plan(runs, specs_by_id, args.budget_usd)

    if args.dry_run:
        print("\ndry run — nothing spent, nothing written.")
        return 0

    results_root = BENCHMARK / "results" / suite_id
    results_root.mkdir(parents=True, exist_ok=True)
    results = []
    spent = 0.0

    for index, run in enumerate(runs, start=1):
        spec = specs_by_id[run["test"]]
        mode = run["mode"]
        label = f"{run['test']}/{mode}"
        ceiling = as_float((spec.get("budget") or {}).get("max_cost_usd"), 0.40)
        if args.budget_usd is not None and spent + ceiling > args.budget_usd:
            print(f"[{index}/{len(runs)}] ABORT — budget ceiling reached (${spent:.4f} spent)")
            break

        print(f"[{index}/{len(runs)}] {label} …", flush=True)
        workspace = Path(tempfile.mkdtemp(prefix="rd-bench-"))
        try:
            outcome = run_one(spec, mode, workspace, args.timeout_s)
            outcome.update({"suite": suite_id, "result_dir": str(results_root / f"{run['test']}-{mode}")})
            result_dir = Path(outcome["result_dir"])
            result_dir.mkdir(parents=True, exist_ok=True)
            result = score(spec, mode, outcome)
            (result_dir / "result.json").write_text(
                json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
            )
            (result_dir / "RESULT.md").write_text(render_result(result), encoding="utf-8")
            results.append(result)
            spent += result["measurements"].get("cost_usd") or 0.0
            print(f"    {result['status']}"
                  + (f" · {result['reality']['outcome']}" if result.get("reality") else "")
                  + (f" · ${result['measurements'].get('cost_usd'):.4f}"
                     if result["measurements"].get("cost_usd") is not None else ""))
        finally:
            if not args.keep_workspaces:
                shutil.rmtree(workspace, ignore_errors=True)

    if not results:
        print("nothing ran", file=sys.stderr)
        return 1

    rows = summarise(results)
    complete_suite = {
        (spec["id"], mode) for spec in built_specs() for mode in MODES
    } <= {(result["test"], result["mode"]) for result in results}
    verdicts = policy_verdicts(rows, complete_suite, args.repeat)
    (results_root / "SUITE.md").write_text(
        render_suite(suite_id, results, rows, verdicts), encoding="utf-8"
    )
    print(f"\nwrote {results_root}/SUITE.md   (spent ${spent:.4f})")
    for verdict in verdicts:
        print(f"  {verdict}")

    if write_status(render_status([{"suite": suite_id, "results": results}])):
        print("  README benchmark status updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
