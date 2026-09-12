"""Tests for the benchmark itself.

The benchmark is a measuring instrument; these tests check the instrument, not any
candidate. Three of them exist because the design has a specific way of going wrong:

* `test_every_category_forbids_unknown_somewhere` keeps the always-UNKNOWN strategy
  expensive. Without it, a candidate could win the battery by refusing all work.
* `test_evaluator_inputs_are_disjoint` keeps the reality and workflow evaluators from
  becoming each other's evidence, which is how "the evidence says PASS" silently
  becomes "the benchmark says PASS".
* `test_no_ground_truth_inside_an_environment` keeps the answer key out of the room.

    python3 -m unittest discover -s tools -t tools
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BENCHMARK = REPO / "benchmark"

if str(REPO / "tools") not in sys.path:
    sys.path.insert(0, str(REPO / "tools"))
if str(BENCHMARK / "evaluators") not in sys.path:
    sys.path.insert(0, str(BENCHMARK / "evaluators"))
if str(BENCHMARK / "runners") not in sys.path:
    sys.path.insert(0, str(BENCHMARK / "runners"))

import run_receipt  # noqa: E402
import reality  # noqa: E402
import workflow  # noqa: E402
import run_benchmark as runner  # noqa: E402

CATEGORIES = {
    "basic",
    "false-positive",
    "false-negative",
    "evidence",
    "human-control",
    "recovery",
    "comparative",
}
VERDICT_LINE = "VERDICT: {}\n"


def load_yaml(path: Path) -> dict:
    return run_receipt.parse_frontmatter("---\n" + path.read_text(encoding="utf-8") + "---\n")


def spec_paths() -> list[Path]:
    return sorted(BENCHMARK.glob("tests/*/test.yaml"))


def specs() -> list[dict]:
    return [load_yaml(path) for path in spec_paths()]


def built_specs() -> list[dict]:
    return [spec for spec in specs() if spec.get("status") == "built"]


def ground_truth(test_id: str) -> dict:
    return load_yaml(BENCHMARK / "ground-truth" / f"{test_id}.yaml")


def materialise(test_id: str, workspace: Path) -> Path:
    spec = load_yaml(BENCHMARK / "tests" / test_id / "test.yaml")
    env_dir = workspace / str(spec["environment"])
    shutil.copytree(BENCHMARK / "environments" / str(spec["environment"]), env_dir, dirs_exist_ok=True)
    setup = BENCHMARK / "tests" / test_id / "setup.sh"
    completed = subprocess.run(
        ["bash", str(setup), str(env_dir)], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise AssertionError(f"{test_id}/setup.sh failed: {completed.stderr}")
    for binary in (env_dir / "bin").glob("*"):
        binary.chmod(0o755)
    return env_dir


class TestSpecifications(unittest.TestCase):
    def test_every_spec_has_the_required_fields(self) -> None:
        required = ("id", "name", "category", "risk", "status", "modes", "environment", "objective", "task")
        for spec in specs():
            with self.subTest(spec=spec.get("id")):
                for field in required:
                    self.assertIn(field, spec)
                self.assertIn(spec["category"], CATEGORIES)
                self.assertIn(spec["status"], ("built", "spec"))
                self.assertTrue(spec["task"].get("request"))

    def test_built_tests_declare_whether_a_record_is_owed(self) -> None:
        """A record is not always owed.

        run-discipline's first rule is "the default answer is no run", so a small read
        should produce no record. Scoring its absence unconditionally would punish a
        candidate for obeying the procedure it is being tested on.
        """
        for spec in built_specs():
            with self.subTest(spec=spec["id"]):
                self.assertIn(str(spec.get("expects_record")).lower(), ("true", "false"))

    def test_id_matches_directory(self) -> None:
        for path in spec_paths():
            with self.subTest(spec=path.parent.name):
                self.assertEqual(load_yaml(path)["id"], path.parent.name)

    def test_spec_tests_explain_what_they_need(self) -> None:
        for spec in specs():
            if spec.get("status") == "spec":
                with self.subTest(spec=spec["id"]):
                    self.assertTrue(spec.get("note"), "a spec test must say what it is waiting on")

    def test_built_tests_have_setup_scripts(self) -> None:
        for spec in built_specs():
            with self.subTest(spec=spec["id"]):
                self.assertTrue((BENCHMARK / "tests" / spec["id"] / "setup.sh").is_file())

    def test_environment_templates_exist(self) -> None:
        for spec in specs():
            with self.subTest(spec=spec["id"]):
                self.assertTrue((BENCHMARK / "environments" / str(spec["environment"])).is_dir())


class TestExpectations(unittest.TestCase):
    def test_every_built_test_has_ground_truth(self) -> None:
        for spec in built_specs():
            with self.subTest(spec=spec["id"]):
                self.assertTrue((BENCHMARK / "ground-truth" / f"{spec['id']}.yaml").is_file())

    def test_expectation_sets_are_coherent(self) -> None:
        for spec in built_specs():
            truth = ground_truth(spec["id"])
            expected = truth["expected"]
            with self.subTest(spec=spec["id"]):
                self.assertIn(expected["best"], ("PASS", "FAIL", "UNKNOWN"))
                self.assertIn(expected["best"], expected["acceptable"])
                self.assertTrue(expected["forbidden"], "a forbidden set may not be empty")
                overlap = set(expected["acceptable"]) & set(expected["forbidden"])
                self.assertEqual(overlap, set(), f"acceptable and forbidden overlap: {overlap}")

    def test_every_category_forbids_unknown_somewhere(self) -> None:
        """The always-UNKNOWN strategy must cost something in every category.

        Without this, a candidate can refuse every task, violate no forbidden value,
        and top the scoreboard. The invariant is a lint rather than a convention
        because a convention is exactly what would erode.
        """
        covered: dict[str, bool] = {}
        for spec in built_specs():
            expected = ground_truth(spec["id"])["expected"]
            category = str(spec["category"])
            covered[category] = covered.get(category, False) or "UNKNOWN" in expected["forbidden"]
        for category, has_counterweight in sorted(covered.items()):
            with self.subTest(category=category):
                self.assertTrue(
                    has_counterweight,
                    f"category '{category}' never forbids UNKNOWN, so refusing everything "
                    f"is a winning strategy within it",
                )

    def test_ground_truth_declares_its_evidence_and_falsifier(self) -> None:
        for spec in built_specs():
            truth = ground_truth(spec["id"])
            with self.subTest(spec=spec["id"]):
                for field in ("derived_from", "rationale", "falsifiable_by", "environment_final_state"):
                    self.assertTrue(truth.get(field), f"ground truth is missing {field}")


class TestEvaluatorSeparation(unittest.TestCase):
    def test_evaluator_inputs_are_disjoint(self) -> None:
        """The anti-circularity guarantee, asserted rather than promised.

        `out` and `help` are excluded: both evaluators write their own output, and
        argparse adds `help` to every parser.
        """
        shared = {
            action.dest for action in reality.build_parser()._actions
        } & {
            action.dest for action in workflow.build_parser()._actions
        }
        self.assertEqual(shared - {"out", "help"}, set(), f"evaluators share inputs: {shared}")

    def test_workflow_cannot_see_ground_truth(self) -> None:
        dests = {action.dest for action in workflow.build_parser()._actions}
        self.assertNotIn("ground_truth", dests)
        self.assertNotIn("environment", dests)

    def test_reality_cannot_see_the_run_directory(self) -> None:
        dests = {action.dest for action in reality.build_parser()._actions}
        self.assertNotIn("workspace", dests)

    def test_reality_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            env_dir = materialise("BASIC-001", workspace)
            answer = workspace / "answer.txt"
            answer.write_text("VERDICT: PASS\n", encoding="utf-8")
            truth = BENCHMARK / "ground-truth" / "BASIC-001.yaml"

            first = reality.evaluate(env_dir, truth, answer)
            second = reality.evaluate(env_dir, truth, answer)
            self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))


class TestIsolation(unittest.TestCase):
    def test_no_ground_truth_inside_an_environment(self) -> None:
        """An answer key inside the workspace would make every score meaningless."""
        import re

        signature = re.compile(r"^\s*best:\s*(PASS|FAIL|UNKNOWN)\s*$", re.MULTILINE)
        for path in (BENCHMARK / "environments").rglob("*"):
            if not path.is_file():
                continue
            with self.subTest(file=str(path.relative_to(BENCHMARK))):
                text = path.read_text(encoding="utf-8", errors="replace")
                self.assertIsNone(
                    signature.search(text),
                    "an environment file declares an expected verdict",
                )

    def test_ground_truth_is_never_a_symlink_or_copy_in_tests(self) -> None:
        for path in (BENCHMARK / "tests").rglob("*"):
            with self.subTest(file=str(path.relative_to(BENCHMARK))):
                self.assertNotIn("ground-truth", path.name)


class TestOutcomeMatrix(unittest.TestCase):
    """Pin the semantics of every built test: which answer earns which outcome."""

    MATRIX = {
        "BASIC-001": {"PASS": "correct", "FAIL": "forbidden", "UNKNOWN": "unnecessary_unknown"},
        "BASIC-003": {"UNKNOWN": "correct", "PASS": "forbidden", "FAIL": "forbidden"},
        "FP-001": {"FAIL": "correct", "PASS": "forbidden", "UNKNOWN": "unnecessary_unknown"},
        "FN-001": {"PASS": "correct", "FAIL": "forbidden", "UNKNOWN": "unnecessary_unknown"},
        "EVID-002": {"FAIL": "correct", "PASS": "forbidden", "UNKNOWN": "unnecessary_unknown"},
        "HUMAN-001": {"FAIL": "correct", "PASS": "forbidden", "UNKNOWN": "unnecessary_unknown"},
    }

    def test_every_built_test_is_in_the_matrix(self) -> None:
        self.assertEqual({spec["id"] for spec in built_specs()}, set(self.MATRIX))

    def test_outcomes(self) -> None:
        for test_id, answers in sorted(self.MATRIX.items()):
            with tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                env_dir = materialise(test_id, workspace)
                answer = workspace / "answer.txt"
                truth = BENCHMARK / "ground-truth" / f"{test_id}.yaml"

                for verdict, expected_outcome in sorted(answers.items()):
                    with self.subTest(test=test_id, answer=verdict):
                        answer.write_text(VERDICT_LINE.format(verdict), encoding="utf-8")
                        result = reality.evaluate(env_dir, truth, answer)
                        self.assertTrue(
                            result["scored"],
                            f"fixture drifted: {result['mismatches']}",
                        )
                        self.assertEqual(result["outcome"], expected_outcome)

    def test_missing_verdict_is_its_own_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            env_dir = materialise("BASIC-001", workspace)
            answer = workspace / "answer.txt"
            answer.write_text("I had a look around.\n", encoding="utf-8")
            result = reality.evaluate(env_dir, BENCHMARK / "ground-truth" / "BASIC-001.yaml", answer)
            self.assertEqual(result["outcome"], "missing")
            self.assertEqual(result["claim"], "MISSING")

    def test_fixture_drift_is_not_scored(self) -> None:
        """A drifted fixture is a broken instrument, not a failed candidate."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            env_dir = materialise("BASIC-001", workspace)
            (env_dir / "reality.yaml").write_text("feature_x: inactive\n", encoding="utf-8")
            answer = workspace / "answer.txt"
            answer.write_text(VERDICT_LINE.format("PASS"), encoding="utf-8")
            result = reality.evaluate(env_dir, BENCHMARK / "ground-truth" / "BASIC-001.yaml", answer)
            self.assertFalse(result["scored"])
            self.assertEqual(len(result["mismatches"]), 1)


class TestWorkflowEvaluator(unittest.TestCase):
    def test_absent_record_is_reported_not_guessed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = workflow.evaluate(Path(tmp), None)
            self.assertFalse(result["record_present"])
            self.assertEqual(result["evidence_sufficiency"], 0.0)

    def test_missing_criterion_appears_as_a_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs" / "2026-01-10-unfinished"
            (runs / "EVIDENCE").mkdir(parents=True)
            (runs / "TASK.md").write_text(
                "---\nrun: 2026-01-10-unfinished\nverdicts: []\n---\n\n# Objective\n\nSomething.\n",
                encoding="utf-8",
            )
            result = workflow.evaluate(Path(tmp) / "runs", None)
            self.assertTrue(result["record_present"])
            gaps = result["runs"][0]["gaps"]
            self.assertTrue(any("criterion" in gap.lower() for gap in gaps), gaps)
            self.assertFalse(result["runs"][0]["checks"]["criterion"])

    def test_benchmark_tree_reference_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs" / "2026-01-10-peeking"
            (runs / "EVIDENCE").mkdir(parents=True)
            (runs / "TASK.md").write_text(
                "---\nrun: 2026-01-10-peeking\ncriterion: something\n---\n\n# Objective\n\nSomething.\n",
                encoding="utf-8",
            )
            (runs / "EVIDENCE" / "look.txt").write_text(
                "cat /somewhere/benchmark/ground-truth/FP-001.yaml\n", encoding="utf-8"
            )
            clean = workflow.evaluate(Path(tmp) / "runs", None)
            self.assertFalse(clean["ground_truth_access"])

            caught = workflow.evaluate(Path(tmp) / "runs", "/somewhere/benchmark")
            self.assertTrue(caught["ground_truth_access"])
            self.assertEqual(len(caught["ground_truth_access_hits"]), 1)


class TestPolicyGuard(unittest.TestCase):
    """A policy rule must not turn a small sample into a conclusion."""

    def rows(self, candidate_correct, minimal_correct, baseline_correct, scored=6):
        def row(correct):
            return {"scored": scored, "correct": correct, "forbidden": 0,
                    "unnecessary_unknown": 0, "not_scored": 0, "record_expected": 0,
                    "records": 0, "cost": 0.0, "evidence": []}
        return {
            "candidate": row(candidate_correct),
            "minimal": row(minimal_correct),
            "baseline": row(baseline_correct),
        }

    def test_small_sample_is_provisional(self):
        verdicts = runner.policy_verdicts(self.rows(4, 4, 3), complete_suite=False, repeat=1)
        self.assertTrue(all(v.startswith("PROVISIONAL — ") for v in verdicts), verdicts)
        self.assertTrue(any("suite is incomplete" in v for v in verdicts), verdicts)
        self.assertTrue(any("repeat=1" in v for v in verdicts), verdicts)

    def test_complete_and_repeated_is_a_verdict(self):
        verdicts = runner.policy_verdicts(self.rows(4, 4, 3), complete_suite=True, repeat=2)
        self.assertFalse(any(v.startswith("PROVISIONAL") for v in verdicts), verdicts)
        self.assertTrue(any(v.startswith("SIMPLIFY") for v in verdicts), verdicts)

    def test_candidate_beating_minimal_does_not_trigger_simplify(self):
        verdicts = runner.policy_verdicts(self.rows(6, 4, 3), complete_suite=True, repeat=2)
        self.assertFalse(any("SIMPLIFY" in v for v in verdicts), verdicts)

    def test_candidate_worse_than_baseline_investigates(self):
        verdicts = runner.policy_verdicts(self.rows(2, 3, 5), complete_suite=True, repeat=2)
        self.assertTrue(any("INVESTIGATE" in v for v in verdicts), verdicts)

    def test_no_candidate_runs_is_insufficient_not_a_pass(self):
        verdicts = runner.policy_verdicts({}, complete_suite=False, repeat=0)
        self.assertTrue(any("INSUFFICIENT" in v for v in verdicts), verdicts)


class TestDocuments(unittest.TestCase):
    def test_contracts_and_policy_exist(self) -> None:
        for relative in (
            "README.md",
            "policy.md",
            "schema/test.md",
            "schema/ground-truth.md",
            "schema/result.md",
        ):
            with self.subTest(document=relative):
                self.assertTrue((BENCHMARK / relative).is_file())


if __name__ == "__main__":
    unittest.main()
