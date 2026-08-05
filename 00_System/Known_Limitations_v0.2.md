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

## v0.3 schema registration status

- The five v0.3 entity schemas (Sector/Security/Product/Technology/Metric) are
  registered (WP-102, RCP-v03-003 approved). **WP-120 has created 9 Sector
  entities and 51 Pilot Core Company entities** (Compute Chain), plus v0.3
  extension fields on the 8 v0.2 Companies. The repository now holds 225
  formal objects across 10 types.
- v0.2 Company objects remain at schema_version=1; v0.3 extension fields
  (region_primary, sector_ids, coverage_tier) were added as new fields only —
  historical tags were not rewritten (R1).
- All new entities start `review_status: pending`; human review (via `review
  apply`) is required before any entity becomes `reviewed`. None are approved
  yet.
- Security/Product/Technology/Metric entities do not exist yet; their indexes
  and CLI commands (`research-os universe ...`) arrive in later WPs.
- Sector IDs and Company IDs in `core_company_ids` / `sector_ids` are format-
  validated but cross-object reference integrity is enforced in WP-103.
- Ontology Assertion (REL-*) schema, predicates and reference checks are
  implemented (WP-103) but **no assertions exist yet** — relation data is
  deferred to a follow-up WP (Phase 0-1 Gate requires 100+ exported + 30
  human-reviewed). Reviewed assertions will require >=1 reviewed Evidence.
- **253 Ontology Assertions created (2026-08-05, relation WP)**: Compute
  Chain value-chain relations (SUPPLIES 184, COMPETES_WITH 32 + symmetric
  reverse, DEPENDS_ON 8, ENABLES 18, PARTNERS_WITH 3). 5 problem relations
  removed in max's spot-check (2 dups, 2 self-refs, 1 wrong semantics).
- **Evidence WP (2026-08-05)**: 10 real public Sources captured + reviewed
  (SEC 10-Q/20-F + exhibits, SK hynix/TSMC/Amazon IR) → 10 Events with
  citation anchors → **22 relations approved** (Gate 30: 22/30). Evidence
  quality calibrated: AWS-OpenAI $100B contract (direct, conf 0.8),
  SK hynix-NVIDIA HBM partnership (direct, conf 0.7), SEC-filing indirect
  (conf 0.3-0.5), weak-inference held pending. **9 relations held
  evidence-insufficient** (sources do not name counterparty). Remaining 8
  for Gate 30 need new named-party capture (Samsung/Micron/Alibaba).
