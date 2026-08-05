# Automation

Automation scripts, prompts, tests and documentation will live here.

No automation may silently approve Evidence or change Thesis confidence.

## Product package

The canonical product code now lives in `src/research_os`. Install an isolated
development environment and run the product doctor:

```bash
python3 -m venv /tmp/ai-research-os-dev-venv
/tmp/ai-research-os-dev-venv/bin/pip install -e ".[dev,ui]"
/tmp/ai-research-os-dev-venv/bin/research-os doctor
source /tmp/ai-research-os-dev-venv/bin/activate
```

The scripts in `09_Automation` are compatibility entry points and require the
product environment to be active. In an iCloud
workspace, prefer a virtual environment outside the synced directory if macOS
marks editable-install `.pth` files as hidden.

## Unified command

M2 product commands:

```bash
research-os project list
research-os project status --id PRJ-001
research-os review queue --project PRJ-001 --status pending
research-os review apply --targets <ID> --decision approve \
  --reviewer <name> --notes "<review note>" --apply
research-os actions list --project PRJ-001
research-os actions overdue --project PRJ-001
research-os metrics --project PRJ-001
research-os index --check --project PRJ-001
```

Review apply is always a dry-run unless `--apply` is explicit. It creates an
immutable Review Decision and updates all targets in one transaction.

M3 Source capture and bounded discovery commands:

```bash
research-os source add --help
research-os source fetch --help
research-os source process --help
research-os source confirm-date --help
research-os source verify-assets
research-os source discover rss --help
research-os source discover github --help
research-os source discover arxiv --help
research-os source discover sec --help
```

Capture/write operations remain dry-run unless `--apply` is explicit. Discovery
is read-only, bounded to 100 candidates and requires an explicit source,
repository, query or CIK/form allowlist.

M4 reviewable generation:

```bash
research-os workflow event --spec <event-spec.json>
research-os workflow report --spec <report-spec.json>
research-os workflow report --spec <weekly-spec.json> \
  --baseline <metrics-snapshot.json>
research-os workflow company-update \
  --company <COM-ID> --events <EVT-ID,...>
```

Templates are `07_Templates/Event_Draft_Spec.json` and
`07_Templates/Report_Draft_Spec.json`. Event/Report creation and Company
proposal writes are dry-run by default. Generation never applies a Review
Decision.

M5 local Dashboard and scheduler:

```bash
research-os ui
research-os jobs run validate
research-os jobs run refresh --project PRJ-001
research-os jobs run source-process --target <SRC-ID>
research-os jobs list --status failed
```

Dashboard v1 is read-only and loopback-only. Scheduler jobs keep append-only
Markdown success/failure records; repeated business effects are idempotent.

Validate all canonical research objects:

```bash
python3 09_Automation/research_os.py validate
```

The validator checks metadata, permanent IDs, references, review invariants,
Taxonomy codes, confidence values and required sections. Warnings are visible
but non-blocking by default; use `--strict` when warnings should fail CI:

```bash
python3 09_Automation/research_os.py validate --strict
```

Check whether machine-maintained indexes match canonical object metadata:

```bash
python3 09_Automation/research_os.py index --check
```

Rebuild the four indexes only after validation succeeds:

```bash
python3 09_Automation/research_os.py index --apply
```

Create Source, Event and Report drafts with the `new-source`, `new-event` and
`new-report` commands. They print a dry-run by default and create a file only
with `--apply`. Run `--help` on each command for its required metadata:

```bash
python3 09_Automation/research_os.py new-source --help
python3 09_Automation/research_os.py new-event --help
python3 09_Automation/research_os.py new-report --help
```

All generated research objects start as `pending`. Existing IDs and files are
never overwritten.

Show the current review queue, Thesis coverage and system health:

```bash
python3 09_Automation/research_os.py status
```

Calculate research-quality metrics or create an immutable JSON baseline:

```bash
python3 09_Automation/research_os.py metrics
python3 09_Automation/research_os.py metrics --format json
python3 09_Automation/research_os.py metrics --snapshot
python3 09_Automation/research_os.py metrics \
  --compare 05_Research/Reviews/Snapshots/METRICS-YYYYMMDD.json
```

Codex workflow prompts live in `09_Automation/prompts/`. The full operating
sequence and error handling are documented in `Workflow_Runbook.md`.

Assess scale triggers, export the derived Ontology, or inspect relationships:

```bash
python3 09_Automation/research_os.py scale
python3 09_Automation/research_os.py export --format jsonl
python3 09_Automation/research_os.py impact --id THS-002 --depth 2
```

SQLite remains a disposable derived view and requires explicit output and
`--apply`; Markdown remains the source of truth:

```bash
python3 09_Automation/research_os.py export \
  --format sqlite \
  --output 09_Automation/derived/research-os.sqlite \
  --apply
```

## Stage 3 review helper

`review_stage3.py` validates the Event table in the Stage 3 review packet.
Without `--apply` it is read-only:

```bash
python3 09_Automation/review_stage3.py
```

After a human fills all 15 decisions and checks the corresponding boxes, apply
only the explicit `approve` and `reject: <reason>` decisions:

```bash
python3 09_Automation/review_stage3.py \
  --apply \
  --reviewer "<name>" \
  --review-date YYYY-MM-DD
```

Safety rules:

- `--apply` requires a reviewer.
- Blank decisions block apply.
- `edit: <instruction>` blocks apply until the requested edit is resolved.
- `reject:` requires a reason.
- The packet must cover exactly the Event files in `04_Evidence/Events`.
- The tool updates Event `review_status`, `updated_at`, and appends an auditable
  review record.
- The tool never changes Thesis confidence or report status.

Run tests:

```bash
/tmp/ai-research-os-dev-venv/bin/pytest \
  --cov=research_os \
  --cov-report=term-missing
```

The compatibility script path remains tested with
`python3 -m unittest discover -s 09_Automation/tests -v` after installing the
product dependencies. Business logic has only one canonical implementation.
