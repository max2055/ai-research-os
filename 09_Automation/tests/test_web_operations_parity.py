from __future__ import annotations

import json
import re
import sqlite3
import tempfile
import unittest
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from research_os.services.mutation_gateway import MutationGateway
from research_os.services.web_operations_mutations import (
    prepare_cadence_review,
    prepare_job_request,
)
from research_os.services.web_repository_mutations import commit_repository_mutation
from research_os.ui.app import create_app
from test_research_os_core import RepositoryValidationTests


class OperationsWebAdapterTests(unittest.TestCase):
    @staticmethod
    def _hidden(page: str, name: str) -> str:
        match = re.search(rf'name="{re.escape(name)}" value="([^"]+)"', page)
        if match is None:
            raise AssertionError(f"missing hidden field {name}")
        return match.group(1)

    def test_job_preview_is_operational_and_does_not_write_thesis(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            prepared = prepare_job_request(
                root,
                actor="max",
                spec_json=json.dumps({"job_name": "validate", "as_of": "2026-08-13"}),
            )
            self.assertEqual("job.run", prepared.preview_input.operation)
            self.assertEqual(
                "operational_human", prepared.preview_input.summary["authority"]
            )
            self.assertNotIn("03_Theses", str(prepared.plan.writes[0].path))

    def test_job_request_uses_frozen_repository_mutation_before_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            prepared = prepare_job_request(
                root,
                actor="max",
                spec_json=json.dumps({"job_name": "validate", "as_of": "2026-08-13"}),
            )
            gateway = MutationGateway(b"s" * 64)
            grant = gateway.issue(prepared.preview_input)
            calls: list[str] = []

            def execute(preview):
                calls.append("request")
                result = commit_repository_mutation(root, preview, prepared.plan)
                self.assertEqual(grant.preview.mutation_id, result["mutation_id"])
                calls.append("runner")
                return {"mutation_id": preview.mutation_id, "status": "success"}

            result = gateway.commit(
                grant.token,
                actor="max",
                operation="job.run",
                target_id="validate",
                current_target_version=lambda _: prepared.preview_input.target_version,
                execute=execute,
            )
            self.assertEqual("success", result["status"])
            self.assertEqual(["request", "runner"], calls)
            self.assertTrue((root / prepared.plan.writes[0].path).is_file())
            db_path = root / "09_Automation/operational/candidates.db"
            with sqlite3.connect(db_path) as db:
                self.assertEqual(
                    1,
                    db.execute(
                        "SELECT COUNT(*) FROM mutation_audit "
                        "WHERE mutation_id = ? AND event_status = 'committed'",
                        (grant.preview.mutation_id,),
                    ).fetchone()[0],
                )

    def test_job_http_preview_commit_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            config = root / "00_System" / "web.local.json"
            config.write_text(
                json.dumps(
                    {"researcher_id": "max", "mutation_signing_secret": "s" * 64}
                ),
                encoding="utf-8",
            )
            config.chmod(0o600)
            client = TestClient(create_app(root), base_url="http://127.0.0.1")
            form = client.get("/operations/jobs/run")
            self.assertEqual(200, form.status_code)
            csrf = self._hidden(form.text, "csrf_token")
            spec = json.dumps({"job_name": "validate", "as_of": "2026-08-13"})
            preview = client.post(
                "/operations/jobs/run/preview",
                content=urlencode({"spec_json": spec, "csrf_token": csrf}),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://127.0.0.1",
                },
            )
            self.assertEqual(200, preview.status_code, preview.text)
            token = self._hidden(preview.text, "preview_token")
            csrf = self._hidden(preview.text, "csrf_token")
            body = urlencode({"preview_token": token, "csrf_token": csrf})
            committed = client.post(
                "/operations/jobs/run/commit",
                content=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://127.0.0.1",
                },
                follow_redirects=False,
            )
            self.assertEqual(303, committed.status_code, committed.text)
            self.assertEqual(200, client.get(committed.headers["location"]).status_code)
            replay = client.post(
                "/operations/jobs/run/commit",
                content=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://127.0.0.1",
                },
            )
            self.assertEqual(409, replay.status_code)

    def test_cadence_review_plan_is_named_and_evaluator_shaped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            (root / "05_Research" / "Projects" / "PRJ-002").mkdir()
            prepared = prepare_cadence_review(
                root,
                actor="max",
                spec_json=json.dumps(
                    {
                        "project_id": "PRJ-002",
                        "cadence": "Weekly",
                        "review_date": "2026-08-13",
                        "metrics_snapshot": (
                            "05_Research/Reviews/Snapshots/METRICS-20260813.json"
                        ),
                        "system_facts": "Validation errors: 0; index drift: 0",
                        "evidence_changes": "No new evidence",
                        "thesis_review": (
                            "Confidence unchanged pending human evidence review"
                        ),
                        "decisions": "Continue pilot observation",
                        "action_items": "Review next week's ingestion failures",
                        "next_review": "2026-08-20",
                    }
                ),
            )
            self.assertEqual("review.cadence", prepared.preview_input.operation)
            self.assertEqual("max", prepared.preview_input.actor)
            self.assertIn("Reviews/Weekly", str(prepared.plan.writes[0].path))
            content = prepared.plan.writes[0].content.decode()
            self.assertIn("Review status: completed", content)
            self.assertIn("Reviewer: max", content)
            self.assertIn("Scope: v0.3 F-021", content)
            self.assertNotIn("03_Theses", str(prepared.plan.writes[0].path))

    def test_cadence_review_http_preview_commit_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            (root / "05_Research" / "Projects" / "PRJ-002").mkdir()
            config = root / "00_System" / "web.local.json"
            config.write_text(
                json.dumps(
                    {"researcher_id": "max", "mutation_signing_secret": "s" * 64}
                ),
                encoding="utf-8",
            )
            config.chmod(0o600)
            client = TestClient(create_app(root), base_url="http://127.0.0.1")
            form = client.get("/reviews/cadence")
            self.assertEqual(200, form.status_code)
            csrf = self._hidden(form.text, "csrf_token")
            spec = json.dumps(
                {
                    "project_id": "PRJ-002",
                    "cadence": "Weekly",
                    "review_date": "2026-08-13",
                    "metrics_snapshot": (
                        "05_Research/Reviews/Snapshots/METRICS-20260813.json"
                    ),
                    "system_facts": "Validation errors: 0; index drift: 0",
                    "evidence_changes": "No new evidence",
                    "thesis_review": "Confidence unchanged",
                    "decisions": "Continue pilot observation",
                    "action_items": "Review next week",
                    "next_review": "2026-08-20",
                }
            )
            preview = client.post(
                "/reviews/cadence/preview",
                content=urlencode({"spec_json": spec, "csrf_token": csrf}),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://127.0.0.1",
                },
            )
            self.assertEqual(200, preview.status_code, preview.text)
            self.assertNotIn("Reviewer:", preview.text)
            token = self._hidden(preview.text, "preview_token")
            csrf = self._hidden(preview.text, "csrf_token")
            body = urlencode({"preview_token": token, "csrf_token": csrf})
            committed = client.post(
                "/reviews/cadence/commit",
                content=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://127.0.0.1",
                },
                follow_redirects=False,
            )
            self.assertEqual(303, committed.status_code, committed.text)
            path = next(
                (root / "05_Research" / "Projects" / "PRJ-002").rglob("WK-*.md")
            )
            self.assertIn("Review status: completed", path.read_text(encoding="utf-8"))
            replay = client.post(
                "/reviews/cadence/commit",
                content=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://127.0.0.1",
                },
            )
            self.assertEqual(409, replay.status_code)


if __name__ == "__main__":
    unittest.main()
