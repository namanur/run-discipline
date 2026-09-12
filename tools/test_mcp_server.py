"""Tests for the skill package and the MCP surface over it.

Two layers of skipping, so the suite is useful in every checkout:

* The MCP tests skip when the optional `mcp` extra is absent.
* The run-dependent tests skip when `runs/` holds no run.

    python3 -m unittest discover -s tools -t tools              # MCP tests skip, no extra needed
    uv run --extra mcp python -m unittest discover -s tools -t tools
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

HAS_MCP = importlib.util.find_spec("mcp") is not None

if HAS_MCP:
    from mcp_server import server

SKILLS_DIR = REPO / "skills"
RUNS_DIR = REPO / "runs"
REQUIRED_SKILLS = {
    "run-discipline",
    "declared-vs-effective",
    "evidence-check",
    "acceptance-review",
    "run-receipt",
    "blind-reconstruction",
}
TOOL_NAMES = {"list_runs", "check_run", "hash_evidence"}
PROVENANCE_KEYS = ("derived_from", "adaptation_reason", "verification", "known_limitations")

SKIP_MCP = "the optional 'mcp' extra is not installed"


def first_run() -> Path | None:
    if not RUNS_DIR.is_dir():
        return None
    for entry in sorted(RUNS_DIR.iterdir()):
        if entry.is_dir() and (entry / "TASK.md").exists():
            return entry
    return None


SAMPLE_RUN = first_run()
SKIP_RUN = "no run directory present under runs/"


def digest_tree(root: Path) -> dict:
    return {
        str(item.relative_to(root)): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(root.rglob("*"))
        if item.is_file()
    }


@unittest.skipUnless(HAS_MCP, SKIP_MCP)
class TestSkillLoading(unittest.TestCase):
    def test_all_six_skills_load(self):
        names = {skill["name"] for skill in server.load_skills()}
        self.assertEqual(names, REQUIRED_SKILLS)

    def test_name_matches_directory(self):
        for skill in server.load_skills():
            with self.subTest(skill=skill["name"]):
                self.assertEqual(skill["name"], skill["path"].parent.name)

    def test_descriptions_are_within_spec(self):
        for skill in server.load_skills():
            with self.subTest(skill=skill["name"]):
                self.assertTrue(skill["description"])
                self.assertLessEqual(len(skill["description"]), 1024)

    def test_descriptions_carry_a_boundary(self):
        for skill in server.load_skills():
            with self.subTest(skill=skill["name"]):
                self.assertIn("Do not use", skill["description"])

    def test_body_excludes_frontmatter(self):
        for skill in server.load_skills():
            with self.subTest(skill=skill["name"]):
                self.assertFalse(skill["body"].lstrip().startswith("---"))
                self.assertIn("#", skill["body"])

    def test_provenance_block_present(self):
        for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(skill=path.parent.name):
                for key in PROVENANCE_KEYS:
                    self.assertIn(key, text)


@unittest.skipUnless(HAS_MCP, SKIP_MCP)
class TestMcpSurface(unittest.TestCase):
    def test_prompts_match_skills(self):
        prompts = asyncio.run(server.mcp.list_prompts())
        self.assertEqual({prompt.name for prompt in prompts}, REQUIRED_SKILLS)

    def test_prompt_body_round_trips(self):
        for name, body in ((s["name"], s["body"]) for s in server.load_skills()):
            with self.subTest(prompt=name):
                result = asyncio.run(server.mcp.get_prompt(name))
                self.assertIn(body, result.messages[0].content.text)

    def test_tools_are_the_read_only_checks(self):
        tools = asyncio.run(server.mcp.list_tools())
        self.assertEqual({tool.name for tool in tools}, TOOL_NAMES)

    def test_references_are_exposed_as_resources(self):
        uris = {str(r.uri) for r in asyncio.run(server.mcp.list_resources())}
        for uri in uris:
            with self.subTest(resource=uri):
                self.assertTrue(uri.startswith("skill://"))


@unittest.skipUnless(HAS_MCP, SKIP_MCP)
class TestNoDuplication(unittest.TestCase):
    """The property that keeps the server from being a second copy of the procedure."""

    def test_prompts_vanish_when_skills_are_absent(self):
        original = server.SKILLS_DIR
        with tempfile.TemporaryDirectory() as empty:
            server.SKILLS_DIR = Path(empty)
            try:
                self.assertEqual(server.load_skills(), [])
            finally:
                server.SKILLS_DIR = original

    def test_server_module_contains_no_procedure_prose(self):
        source = (REPO / "mcp_server" / "server.py").read_text(encoding="utf-8")
        for marker in ("declared vs effective", "A-G", "blind reconstruction", "five-line"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


@unittest.skipUnless(HAS_MCP, SKIP_MCP)
class TestTools(unittest.TestCase):
    def test_resolve_run_rejects_escape(self):
        for candidate in ("../..", "/etc", "does-not-exist", "..", ""):
            with self.subTest(run=candidate):
                with self.assertRaises(ValueError):
                    server.resolve_run(candidate)

    def test_list_runs_returns_a_list(self):
        rows = json.loads(asyncio.run(server.mcp.call_tool("list_runs", {})).content[0].text)
        self.assertIsInstance(rows, list)
        self.assertEqual(len(rows), len([r for r in RUNS_DIR.iterdir() if r.is_dir()])
                         if RUNS_DIR.is_dir() else 0)

    def test_check_run_rejects_a_missing_run(self):
        with self.assertRaises(ValueError):
            server.resolve_run("no-such-run")


@unittest.skipUnless(HAS_MCP and SAMPLE_RUN, SKIP_MCP if not HAS_MCP else SKIP_RUN)
class TestRunDependentTools(unittest.TestCase):
    """Exercised against whatever run is present. Skipped in a fresh checkout."""

    def test_list_runs_describes_the_run(self):
        rows = json.loads(asyncio.run(server.mcp.call_tool("list_runs", {})).content[0].text)
        sample = next(row for row in rows if row["run"] == SAMPLE_RUN.name)
        self.assertIn("tier", sample)
        self.assertIn("override_recorded", sample)
        self.assertGreaterEqual(sample["evidence_files"], 0)

    def test_check_run_returns_a_gap_list(self):
        payload = json.loads(
            asyncio.run(
                server.mcp.call_tool("check_run", {"run": SAMPLE_RUN.name})
            ).content[0].text
        )
        self.assertEqual(payload["run"], SAMPLE_RUN.name)
        self.assertEqual(payload["gap_count"], len(payload["gaps"]))
        self.assertIsInstance(payload["gaps"], list)

    def test_hash_evidence_covers_every_file(self):
        payload = json.loads(
            asyncio.run(
                server.mcp.call_tool("hash_evidence", {"run": SAMPLE_RUN.name})
            ).content[0].text
        )
        evidence_dir = SAMPLE_RUN / "EVIDENCE"
        expected = (
            sorted(item.name for item in evidence_dir.iterdir() if item.is_file())
            if evidence_dir.is_dir()
            else []
        )
        self.assertEqual(sorted(payload["files"]), expected)
        for digest in payload["files"].values():
            self.assertEqual(len(digest), 64)

    def test_tools_modify_nothing(self):
        before = digest_tree(SAMPLE_RUN)
        asyncio.run(server.mcp.call_tool("list_runs", {}))
        asyncio.run(server.mcp.call_tool("check_run", {"run": SAMPLE_RUN.name}))
        asyncio.run(server.mcp.call_tool("hash_evidence", {"run": SAMPLE_RUN.name}))
        self.assertEqual(before, digest_tree(SAMPLE_RUN))


if __name__ == "__main__":
    unittest.main()
