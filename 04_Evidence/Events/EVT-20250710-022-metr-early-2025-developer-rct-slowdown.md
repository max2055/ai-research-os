---
id: EVT-20250710-022
type: event
title: "METR randomized trial finds early-2025 AI tools slowed experienced developers"
created_at: 2026-07-29
updated_at: '2026-07-30'
schema_version: 1
project_ids: [PRJ-002]
status: active
review_status: reviewed
event_date: 2025-07-10
source_ids: [SRC-20260729-030]
companies: []
technologies: [DEV-EVALUATION, DEV-AGENT-FRAMEWORK]
products: []
thesis_links: [THS-006, THS-008]
confidence: 0.76
generation_method: structured
generation_fingerprint: 51ca23c8303c9f58070ca9d629c32dfc76d6e715e8f1c0cde54ddf0d7fab93cb
citation_anchors:
- fact_id: F1
  source_id: SRC-20260729-030
  asset_path: "01_Inbox/_assets/SRC-20260729-030/20260729160425-b6d4a8e7d8ae.pdf.extracted.txt"
  locator: L6-L12
  quote: "Despite widespread adoption, the impact of AI tools on software development in\nthe wild remains understudied. We conduct a randomized controlled trial (RCT)\nto understand how AI tools at the February–June 2025 frontier affect the produc-\ntivity of experienced open-source developers. 16 developers with moderate AI\nexperience complete 246 tasks in mature projects on which they have an aver-\nage of 5 years of prior experience. Each task is randomly assigned to allow or\ndisallow usage of early-2025 AI tools."
  quote_sha256: 9157c01390f36e7cadade1f2baa4e171a2a575eb26bc1eea1325992a39a4a7ab
- fact_id: F2
  source_id: SRC-20260729-030
  asset_path: "01_Inbox/_assets/SRC-20260729-030/20260729160425-b6d4a8e7d8ae.pdf.extracted.txt"
  locator: L12-L13
  quote: "When AI tools are allowed, developers\nprimarily use Cursor Pro, a popular code editor, and Claude 3.5/3.7 Sonnet."
  quote_sha256: d45dde2ba8dad07eca3422e83bf3afbfe848396ee72a69bf8b0cf9e5dad15c6f
- fact_id: F3
  source_id: SRC-20260729-030
  asset_path: "01_Inbox/_assets/SRC-20260729-030/20260729160425-b6d4a8e7d8ae.pdf.extracted.txt"
  locator: L13-L19
  quote: "Be-\nfore starting tasks, developers forecast that allowing AI will reduce completion\ntime by 24%. After completing the study, developers estimate that allowing AI\nreduced completion time by 20%. Surprisingly, we find that allowing AI actually\nincreases completion time by 19%—AI tooling slowed developers down. This\nslowdown also contradicts predictions from experts in economics (39% shorter)\nand ML (38% shorter)."
  quote_sha256: 5bcce6c7f347a9833bbc6692918cd9aa3498338013545abe0f4be093e510ab3e
source_independence_groups: [["SRC-20260729-030"]]
tags: [APP-CODING, MAT-RESEARCH, EV-TECHNOLOGY]
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

- **F1** — METR ran a randomized controlled trial with 16 experienced open-source developers completing 246 tasks in mature projects.
  - Source: `SRC-20260729-030`
  - Anchor: `01_Inbox/_assets/SRC-20260729-030/20260729160425-b6d4a8e7d8ae.pdf.extracted.txt#L6-L12`
  - Quote: "Despite widespread adoption, the impact of AI tools on software development in\nthe wild remains understudied. We conduct a randomized controlled trial (RCT)\nto understand how AI tools at the February–June 2025 frontier affect the produc-\ntivity of experienced open-source developers. 16 developers with moderate AI\nexperience complete 246 tasks in mature projects on which they have an aver-\nage of 5 years of prior experience. Each task is randomly assigned to allow or\ndisallow usage of early-2025 AI tools."
- **F2** — Participants primarily used Cursor Pro and Claude 3.5/3.7 Sonnet when AI was allowed.
  - Source: `SRC-20260729-030`
  - Anchor: `01_Inbox/_assets/SRC-20260729-030/20260729160425-b6d4a8e7d8ae.pdf.extracted.txt#L12-L13`
  - Quote: "When AI tools are allowed, developers\nprimarily use Cursor Pro, a popular code editor, and Claude 3.5/3.7 Sonnet."
- **F3** — METR found that allowing AI increased completion time by 19%, contrary to developer and expert forecasts.
  - Source: `SRC-20260729-030`
  - Anchor: `01_Inbox/_assets/SRC-20260729-030/20260729160425-b6d4a8e7d8ae.pdf.extracted.txt#L13-L19`
  - Quote: "Be-\nfore starting tasks, developers forecast that allowing AI will reduce completion\ntime by 24%. After completing the study, developers estimate that allowing AI\nreduced completion time by 20%. Surprisingly, we find that allowing AI actually\nincreases completion time by 19%—AI tooling slowed developers down. This\nslowdown also contradicts predictions from experts in economics (39% shorter)\nand ML (38% shorter)."

## Inferences

- At least in this early-2025 setting, perceived productivity and forecast productivity materially diverged from measured completion time.
- Agent adoption and subjective satisfaction cannot be treated as sufficient evidence of economic productivity.

## Research judgment

This is stronger causal evidence than vendor claims or surveys, but external validity is bounded by 16 experienced maintainers, their own mature repositories and early-2025 tools. It is a direct contradiction to universal productivity claims, not proof that later agents or other task types always slow developers.

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| THS-006 | contradicting | The result challenges the assumption that moving from assistance to delegated work automatically improves developer productivity. | 0.00, pending human review |
| THS-008 | contradicting | A measured slowdown in a realistic task setting challenges favorable unit-economics assumptions based only on adoption or perceived time saving. | 0.00, pending human review |

## Source independence

| Group | Sources | Treatment |
|---|---|---|
| IG-01 | SRC-20260729-030 | independent root |

## Alternative explanations

- Later models and agentic tools may perform materially better than the February–June 2025 tool frontier.
- Experienced maintainers in familiar repositories may have less room for AI assistance than other developer cohorts.

## Unknowns

- The result does not determine effects on code quality, documentation, learning or longer-horizon output.
- The effect for autonomous background agents and greenfield tasks is not established.

## Follow-up indicators

- Track replications using current agentic tools and larger developer samples.
- Measure quality-adjusted output and total review/rework time, not completion time alone.
