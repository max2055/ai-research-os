from __future__ import annotations

import json
import tempfile
import unittest

from research_os.services.web_operations_mutations import prepare_job_request
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


if __name__ == "__main__":
    unittest.main()
