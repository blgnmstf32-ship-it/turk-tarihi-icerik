"""Regression tests for least privilege and safe requirements handling."""

from pathlib import Path
import tempfile
import unittest

from packaging.requirements import InvalidRequirement

from scripts.dependency_security import (
    EARSHOT, EARSHOT_REQUIREMENTS, WRITE_JOBS, permissions_findings, requirement_lines,
)


class DependencySecurityTests(unittest.TestCase):
    def test_explicit_read_scope_passes(self):
        workflow = {"on": {"pull_request": ""}, "permissions": {"contents": "read"}, "jobs": {"scan": {}}}
        self.assertEqual(permissions_findings("scan.yml", workflow), [])

    def test_token_defaults_and_job_writes_are_blocked(self):
        findings = permissions_findings("scan.yml", {"jobs": {"scan": {"permissions": "write-all"}}})
        self.assertEqual(len(findings), 2)

    def test_audit_rejects_secrets_and_privileged_pr_trigger(self):
        workflow = {"on": {"pull_request_target": ""}, "permissions": {},
                    "jobs": {"security": {"secrets": "inherit", "env": {"KEY": "${{ secrets.TEST_ONLY }}"}}}}
        self.assertEqual(len(permissions_findings("dependency_security.yml", workflow)), 3)

    def test_required_ledger_writes_require_exact_guard_and_event(self):
        for (name, job), (triggers, guard) in WRITE_JOBS.items():
            with self.subTest(workflow=name):
                workflow = {"on": triggers, "permissions": {"contents": "read"},
                            "jobs": {job: {"if": guard, "permissions": {"contents": "write"}}}}
                self.assertEqual(permissions_findings(name, workflow), [])
                workflow["on"] = {"pull_request": ""}
                self.assertEqual(len(permissions_findings(name, workflow)), 1)

    def test_dependency_resolution_rejects_direct_urls_and_index_directives(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "requirements.txt"
            path.write_text("test @ https://example.invalid/test.whl\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                list(requirement_lines(path))
            path.write_text("--extra-index-url https://example.invalid/simple\n", encoding="utf-8")
            with self.assertRaises(InvalidRequirement):
                list(requirement_lines(path))

    def test_only_exact_reviewed_earshot_reference_uses_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "requirements-media-pilot.txt"
            path.write_text(EARSHOT + "\n", encoding="utf-8")
            self.assertEqual(list(requirement_lines(path, allow_earshot=True)), list(EARSHOT_REQUIREMENTS))
            with self.assertRaises(ValueError):
                list(requirement_lines(path))


if __name__ == "__main__":
    unittest.main()
