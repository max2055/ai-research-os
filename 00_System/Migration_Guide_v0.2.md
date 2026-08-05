# AI Research OS v0.2 Migration Guide

Status: release candidate guide  
Updated: 2026-07-29

## Supported starting point

This guide covers the repository baseline before productization and the migrations
recorded in:

- `00_System/M2_Migration_Record.md`
- `00_System/M3_Migration_Record.md`

Do not run migrations on the only copy of a Vault. Commit or back up Markdown and
Source assets first.

## Upgrade

```bash
python3 -m venv /tmp/ai-research-os-v02-venv
/tmp/ai-research-os-v02-venv/bin/pip install -e ".[dev,ui]"
/tmp/ai-research-os-v02-venv/bin/research-os doctor
/tmp/ai-research-os-v02-venv/bin/research-os validate
/tmp/ai-research-os-v02-venv/bin/research-os index --apply
/tmp/ai-research-os-v02-venv/bin/research-os index --check
```

Then inspect migration state without changing files:

```bash
research-os doctor
research-os validate
```

v0.2 does not expose an open-ended migration CLI. The repository's v0.2 migrations
were release-specific, were applied through the tested `MigrationEngine`, and are
recorded in the two migration records above. A future migration must ship with its
own approved RCP, deterministic migration definition, dry-run plan and rollback
instructions; users must not improvise a generic field rewrite.

## Data changes in v0.2

- Managed objects use formal Pydantic Schema version `1`.
- Core objects have `schema_version` and `project_ids`.
- Project, Review Decision, Action and Job Run are formal objects.
- Source provenance fields include canonical URL, asset paths, content hash, fetch
  time, upstream Source IDs and processing state.
- Event and Report generated-draft fields are additive and remain pending until a
  Review Decision is applied.

Migration code must preserve manual body text and unknown front matter. It must be
idempotent and must refuse a precondition hash mismatch.

## Compatibility

The installed `research-os` command is canonical. The legacy entry point
`python3 09_Automation/research_os.py ...` remains available for one v0.2 release
cycle and delegates to the same product runtime.

## Rollback

For a migration executed locally through `MigrationEngine`, use its recorded rollback
only when the ignored local backup manifest still exists and all precondition hashes
match. Otherwise restore the committed Markdown state from Git and Source assets
from the separate encrypted backup. Never reconstruct authoritative Markdown from
an index, Dashboard response, JSONL or SQLite export.
