# AI Research OS v0.2 Release Notes

Status: draft — release gate pending
Prepared: 2026-07-30
Package version during pilot: `0.2.0.dev0`

## Release decision

This document is prepared for the v0.2 release candidate. It is not a declaration
that v0.2 has shipped. `research-os release check` remains authoritative for the
machine-verifiable checklist, and the final release requires an explicit human
decision in `05_Research/Projects/PRJ-002/Pilot_Gate.md`.

## Highlights

- Installable Python package with one typed runtime and a stable CLI.
- Formal, round-trip-safe Markdown schemas and idempotent migrations.
- Multi-project scoping, immutable Review Decisions and structured Actions.
- URL/local-file Source capture, immutable assets, SHA-256 provenance, versioning,
  extraction, deduplication and bounded discovery adapters.
- Anchored Event drafts, reviewed-Evidence Report synthesis, incremental baselines,
  contradiction preservation and Company update proposals.
- Local read-only FastAPI/HTMX Dashboard, Obsidian dashboards and auditable,
  idempotent scheduler jobs.
- Synthetic 1,000 Source / 500 Event benchmark and explicit release-readiness gates.
- PRJ-002 AI Coding Agent pilot with 12 reviewed archived Sources, 9 reviewed anchored
  Events, a passed 10-Source/23-Fact field Gate and a reviewed final Report.
- PRJ-001 quality expansion with six archived Sources and six reviewed anchored Events:
  named production cases, direct THS-001/THS-005 counterevidence and explicit
  separation of Microsoft Agent seats, usage, credits, managed objects and revenue.
- YAML-safe Source generation for titles and publishers containing punctuation, with
  a regression test for colon-bearing scalars.
- Completion-audit hardening that adds the previously omitted RQ-07/RQ-08 Actions to
  release readiness and requires evidence rows and elapsed-time thresholds for
  recovery and performance Gates.
- Eight separately reviewed Company profiles plus an approved source-governed
  valuation and market-expectations contract and a dated Microsoft worksheet.
- Clean-clone recovery of Git plus 144 real Source-asset files from an encrypted
  archive, covering all 36 currently processed Sources and 166 formal objects.

## Research-governance guarantees

- Markdown remains the only authoritative research store.
- Generated Source, Event, Thesis, Company and Report work remains pending by
  default.
- The system does not automatically approve research judgment or raise Thesis
  confidence.
- Supporting, contradicting and unknown information remain explicit.
- Raw Source material is never silently overwritten.

## Upgrade and recovery

- Migration: `00_System/Migration_Guide_v0.2.md`
- Recovery: `00_System/Recovery_Runbook.md`
- Limitations: `00_System/Known_Limitations_v0.2.md`
- Human review sequence: `05_Research/Reviews/v0.2_Human_Review_Runbook.md`

## Pending before final tag

- Complete two real Weekly cycles and one Monthly review.
- Record the human release decision and rerun `research-os release check`.
