---
id: EVT-20260607-027
type: event
title: "Nubank reports A/B-tested results for five production customer-support agents"
created_at: 2026-07-30
updated_at: '2026-07-30'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2026-06-07
source_ids: [SRC-20260730-034]
companies: []
technologies: [DEV-AGENT-FRAMEWORK, DEV-EVALUATION, DEV-ORCHESTRATION]
products: []
thesis_links: [THS-002, THS-004]
confidence: 0.82
generation_method: structured
generation_fingerprint: 40e42ecec2ae06cb2d0828e9b52804b6f41aec1a3311084b4129308d459c132f
citation_anchors:
- fact_id: F1
  source_id: SRC-20260730-034
  asset_path: "01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf.extracted.txt"
  locator: L255
  quote: "Figure 3: Online A/B-test gains for five production agents"
  quote_sha256: 7b0a2c6cb7cf53beba4f72566d20794debcbfc3ea6b9c7c5279960bf8bab4baa
- fact_id: F2
  source_id: SRC-20260730-034
  asset_path: "01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf.extracted.txt"
  locator: L915
  quote: "Card Delivery+37+29−10"
  quote_sha256: e331c990b0ccc1fcabcaeaa43172e291101b6cb851903e0a67ec21f1625fa5ad
- fact_id: F3
  source_id: SRC-20260730-034
  asset_path: "01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf.extracted.txt"
  locator: L919
  quote: "Product Explainer+12.3−1.5 ‡ −6.2"
  quote_sha256: 367e4f1a3ad9eea0d8396439b68b1a4abb5e624b5cba129d60803bf17e852c40
- fact_id: F4
  source_id: SRC-20260730-034
  asset_path: "01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf.extracted.txt"
  locator: L912
  quote: "gap in the hardest domain (debt management,−23.6p.p.)."
  quote_sha256: 457fb1fc9078c8b89b67bbb69397e70484ac5a135c6aa996c21942eb8e564955
- fact_id: F5
  source_id: SRC-20260730-034
  asset_path: "01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf.extracted.txt"
  locator: L156
  quote: "minimum human-agreement thresholds before"
  quote_sha256: cdfeb0721fa6de6a34e54ea0ec37c20ee9f2de4413e3044dbd125f42d3b7c52d
source_independence_groups: [["SRC-20260730-034"]]
tags: [EV-CUSTOMER, EV-TECHNOLOGY, MAT-SCALE, APP-CRM]
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

- **F1** — Nubank reports five production agents covering card delivery, debt management, credit-limit support, card management and product explanation.
  - Source: `SRC-20260730-034`
  - Anchor: `01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf.extracted.txt#L255`
  - Quote: "Figure 3: Online A/B-test gains for five production agents"
- **F2** — For the card-delivery agent, the reported online A/B-test gains were 37 percentage points in AI transactional NPS and 29 percentage points in self-service rate, while AI tNPS remained 10 points below expert human agents.
  - Source: `SRC-20260730-034`
  - Anchor: `01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf.extracted.txt#L915`
  - Quote: "Card Delivery+37+29−10"
- **F3** — For Product Explainer, the reported tNPS gain was 12.3 percentage points, self-service rate declined 1.5 points and AI tNPS remained 6.2 points below expert humans.
  - Source: `SRC-20260730-034`
  - Anchor: `01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf.extracted.txt#L919`
  - Quote: "Product Explainer+12.3−1.5 ‡ −6.2"
- **F4** — Four of five deployed agents were reported within approximately 1–10 percentage points of expert human-agent tNPS; debt management remained 23.6 points below.
  - Source: `SRC-20260730-034`
  - Anchor: `01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf.extracted.txt#L912`
  - Quote: "gap in the hardest domain (debt management,−23.6p.p.)."
- **F5** — The reported automated-evaluation pipeline enforced minimum human-agreement thresholds before trusting automated judgments.
  - Source: `SRC-20260730-034`
  - Anchor: `01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf.extracted.txt#L156`
  - Quote: "minimum human-agreement thresholds before"

## Inferences

- The case links production impact to an evaluation and context-engineering system, not to model capability alone.
- Outcome variance across domains indicates that the economic and service value of an agent is task-specific.
- Remaining gaps to expert humans and the Product Explainer self-service decline argue for per-workflow release gates.

## Research judgment

The paper is a strong named production case with online metrics and explicit human baselines. It supports the importance of evaluation, context and operations as enterprise control points. Because all five deployments are within Nubank and the authors are the deploying team, this is one independent organization case, not five independent customers, and it does not establish product revenue or general market adoption.

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| THS-002 | supporting | Versioned context, tools, evaluation and online measurement are presented as the reusable production system behind five deployed agents. | 0.00, pending human review |
| THS-004 | contextual | A large incumbent service organization can build and operate agents at scale, but this case does not identify which software vendor captures the value. | 0.00, pending human review |

## Source independence

| Group | Sources | Treatment |
|---|---|---|
| IG-01 | SRC-20260730-034 | independent root |

## Alternative explanations

- Improvements may reflect better prompts and workflow engineering relative to weak prior agent variants rather than an enduring moat.
- A/B-test gains within one company may not transfer to other data, languages or service processes.
- Customer-satisfaction improvements may not translate into lower total service cost.

## Unknowns

- Absolute tNPS, contact volumes, model and infrastructure costs are not fully disclosed.
- Long-run retention, compliance incidents and human staffing effects are unknown.
- The external software vendors and commercial terms behind the stack are not disclosed.

## Follow-up indicators

- Track absolute satisfaction, containment, cost per resolution and human escalation by use case.
- Seek a second organization using a comparable evaluation-driven system.
- Identify which platform layers are purchased versus built internally.
