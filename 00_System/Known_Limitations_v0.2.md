# AI Research OS v0.2 Known Limitations

Status: reviewed for release candidate  
Updated: 2026-07-30

## Product boundary

- The product is local-first and single-user. The Dashboard is read-only and only
  binds to loopback; there is no multi-user server, account or permission model.
- Review, editing and final publication use Markdown and CLI workflows rather than
  Web mutation endpoints.
- Markdown scanning is the default query layer. SQLite and JSONL are disposable
  exports, and there is no always-on database or vector store.
- Scheduler commands are entry points for an OS scheduler; the package does not run
  a resident scheduling daemon.
- The tested migration engine is available to release engineering, but v0.2 does not
  expose a generic end-user migration CLI. Each future schema migration must ship as
  a reviewed, version-specific operation with its own plan and rollback record.

## Source capture

- URL capture is bounded single-resource retrieval, not a browser crawler. Pages
  requiring interactive login, client-side rendering, anti-bot bypass or prohibited
  access are not automatically archived.
- Scanned PDFs require an external OCR step. Extraction failure stays visible as
  `failed`; the system does not invent text.
- Source assets are excluded from Git by default for copyright, privacy and size
  reasons. Recovery from an encrypted archive has been tested, but a durable
  off-device destination and key-recovery policy still require owner configuration.
- Three pre-M3 Sources remain registered because standard capture returned HTTP 403
  or timed out. Their Source records were human-approved with the missing-archive
  limitation explicit; no asset was fabricated.
  The other 17 pre-M3 Sources have since been archived and processed.

## Research quality

- AI draft quality is bounded by the captured Source. Exact anchors improve
  traceability but do not replace human interpretation or attribution review.
- Source independence is researcher-specified; common upstream material may still
  be missed.
- Automated investment valuation, portfolio execution and security recommendations
  are outside v0.2. RQ-08 includes one source-governed Microsoft worksheet, but it is
  a reproducible expectations baseline rather than a DCF, target price or advice.
- All current Source and Event records have human decisions; repository validation
  has zero `REV003` warnings. The three capture exceptions remain visible.
- Six new PRJ-001 Events add independent production cases, direct counterevidence and
  commercial-metric separation with individual human Review Decisions.

## Release-candidate gaps

- M4 accuracy, Source/Event review, Company review, research-quality Actions and the
  first PRJ-002 Report are complete.
- PRJ-002 has 12 reviewed Sources, 9 reviewed Events and one reviewed final Report.
  Its three Thesis hypotheses remain pending and retain their initial confidence.
- Two real Weekly reviews, one real Monthly review and the post-cycle release decision
  remain pending; cadence records cannot be backfilled before their dates.
- A private remote and remote CI are not configured in the current local repository.
  Clean-clone testing is used locally, but off-device Git backup must be configured
  by the owner.

## Deferred scale choices

The M6 synthetic baseline passes at 1,000 Sources and 500 Events. A permanent
database, graph store or vector index should only be reconsidered after a measured
query bottleneck or a stable high-frequency relationship-query requirement.
