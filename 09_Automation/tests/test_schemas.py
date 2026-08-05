from __future__ import annotations

import tempfile
import unittest
from collections import Counter
from pathlib import Path

try:
    from pydantic import ValidationError

    from research_os.repositories.markdown import (
        MarkdownDocument,
        load_documents,
        validate_documents,
    )
    from research_os.schemas import EventSchema
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run Schema tests") from exc

ROOT = Path(__file__).resolve().parents[2]


class SchemaTests(unittest.TestCase):
    def test_all_repository_objects_pass_formal_schemas(self) -> None:
        documents, errors = validate_documents(ROOT)
        self.assertEqual([], errors)
        self.assertEqual(
            {
                "action": 12,
                "company": 8,
                "event": 31,
                "project": 2,
                "report": 2,
                "review": 64,
                "source": 39,
                "thesis": 8,
            },
            dict(Counter(document.metadata["type"] for document in documents)),
        )

    def test_noop_round_trip_is_byte_exact_for_all_objects(self) -> None:
        for document in load_documents(ROOT):
            self.assertEqual(document.original_text, document.render())

    def test_round_trip_edit_preserves_body_unknown_fields_and_comments(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "SRC-20260729-001-test.md"
            path.write_text(
                """---
id: SRC-20260729-001
type: source
title: Test
created_at: 2026-07-29
updated_at: 2026-07-29
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: pending
tags: []
source_type: article
publisher: Publisher
authors: []
published_at: 2026-07-29
accessed_at: 2026-07-29
url: https://example.com
local_path:
source_grade: A
companies: []
technologies: []
products: []
canonical_url: https://example.com
asset_paths: []
content_sha256:
fetched_at:
upstream_source_ids: []
processing_status: registered
processing_error:
published_date_proposal:
custom_field: keep  # human comment
---
# Body

Manual text.
""",
                encoding="utf-8",
            )
            document = MarkdownDocument.read(path)
            original_body = document.body
            document.set_metadata("updated_at", "2026-07-30")
            rendered = document.render()
            path.write_text(rendered, encoding="utf-8")
            reparsed = MarkdownDocument.read(path)
            self.assertEqual(original_body, reparsed.body)
            self.assertEqual("keep", reparsed.metadata["custom_field"])
            self.assertIn("# human comment", rendered)

    def test_schema_rejects_invalid_event_id(self) -> None:
        with self.assertRaises(ValidationError):
            EventSchema.model_validate(
                {
                    "id": "BAD",
                    "type": "event",
                    "title": "Bad",
                    "created_at": "2026-07-29",
                    "updated_at": "2026-07-29",
                    "schema_version": 1,
                    "project_ids": ["PRJ-001"],
                    "status": "active",
                    "review_status": "pending",
                    "tags": [],
                    "event_date": "2026-07-29",
                    "source_ids": ["SRC-20260729-001"],
                    "companies": [],
                    "technologies": [],
                    "products": [],
                    "thesis_links": [],
                    "confidence": 0.5,
                }
            )


if __name__ == "__main__":
    unittest.main()
