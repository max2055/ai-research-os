from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest

from research_os.services.mutation_gateway import MutationGateway
from research_os.services.web_operations_mutations import prepare_job_request
from research_os.services.web_repository_mutations import commit_repository_mutation
from test_research_os_core import RepositoryValidationTests


class OperationsWebAdapterTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
