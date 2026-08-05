---
id: EVT-20260605-030
type: event
title: "Five Agentforce cases show production agents bounded by data, logic and human controls"
created_at: 2026-07-30
updated_at: '2026-07-30'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2026-06-05
source_ids: [SRC-20260730-037]
companies: []
technologies: [DEV-AGENT-FRAMEWORK, DEV-EVALUATION, DEV-ORCHESTRATION]
products: []
thesis_links: [THS-001, THS-002, THS-004]
confidence: 0.68
generation_method: structured
generation_fingerprint: 5f62b8bdcc130d97dfbff1e5890fc8a3f2c6bf550eaf46d1d8c1b690041f082f
citation_anchors:
- fact_id: F1
  source_id: SRC-20260730-037
  asset_path: "01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt"
  locator: L17
  quote: "They scoped the agent to public Salesforce Knowledge articles only and built explicit escalation paths for anything sensitive."
  quote_sha256: b1b0f6271b934dc1baebb956e987063c9393e619d6913748b4563079a867bb68
- fact_id: F2
  source_id: SRC-20260730-037
  asset_path: "01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt"
  locator: L18
  quote: "Agentforce Voice now handles 75% of business-hours calls and 100% of after-hours calls."
  quote_sha256: 56ff386c52e7c4824df66f86c0b96a0210bef345d030f3ce232f4b7a728b740e
- fact_id: F3
  source_id: SRC-20260730-037
  asset_path: "01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt"
  locator: L24
  quote: "With Agentforce, Adecco’s prescreening coverage went from 10% to 100%."
  quote_sha256: a67e4ec1ac4a5e1d1b9fb15a06b06a57d3a404ffa9a4fe8f31d90f93da26e350
- fact_id: F4
  source_id: SRC-20260730-037
  asset_path: "01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt"
  locator: L28
  quote: "find the decisions that couldn’t tolerate that ambiguity and replace them with conditional logic"
  quote_sha256: f0296256912bfe8f0de180b610db8eb14c3d180bd5f0359115166be10efce435
- fact_id: F5
  source_id: SRC-20260730-037
  asset_path: "01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt"
  locator: L30
  quote: "Conversation failure rate dropped from roughly 33% to about 0.5%. Deflection climbed from the low 60s to a sustained average of 82%, running between 81% and 84% week to week. CSAT held at 4.8 out of 5, matching the performance of the live human support team."
  quote_sha256: bff191aba4f496cc208b8557da2a157e40a4f950684888a50959609312820e3b
- fact_id: F6
  source_id: SRC-20260730-037
  asset_path: "01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt"
  locator: L33
  quote: "Indeed runs Agentforce across four production use cases:"
  quote_sha256: 4cb5ebde807584473dd09f7f3e3510bc63a77542a6a91313784cfadd52d33b2b
- fact_id: F7
  source_id: SRC-20260730-037
  asset_path: "01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt"
  locator: L34
  quote: "Indeed’s engineers build through APIs and a CLI."
  quote_sha256: fe7a555690ff0329992ed55be45cb4b9f2e291f591fd454d69a4606ecc59d624
- fact_id: F8
  source_id: SRC-20260730-037
  asset_path: "01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt"
  locator: L40
  quote: "The company also runs weekly conversation engineering meetings and structured learning sessions after every major iteration."
  quote_sha256: 0e250cb714216403e323369306fc6d14810a796ea3a70f3aef25bd5608e0bc92
- fact_id: F9
  source_id: SRC-20260730-037
  asset_path: "01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt"
  locator: L40
  quote: "The Digital Concierge has now handled more than 250,000 conversations."
  quote_sha256: 95ff1475ebd0cafc716a72ab42cd6e1a4edc662c3971454a7e3d809322cfce24
source_independence_groups: [["SRC-20260730-037"]]
tags: [EV-CUSTOMER, EV-TECHNOLOGY, MAT-PRODUCTION, APP-CRM]
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

- **F1** — Florida Prepaid scoped its voice agent to public Salesforce Knowledge and retained explicit human escalation for sensitive matters.
  - Source: `SRC-20260730-037`
  - Anchor: `01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt#L17`
  - Quote: "They scoped the agent to public Salesforce Knowledge articles only and built explicit escalation paths for anything sensitive."
- **F2** — Salesforce reported that Florida Prepaid's agent handled 75% of business-hours and all after-hours calls.
  - Source: `SRC-20260730-037`
  - Anchor: `01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt#L18`
  - Quote: "Agentforce Voice now handles 75% of business-hours calls and 100% of after-hours calls."
- **F3** — Adecco placed completeness and discrimination checks on job postings before agent prescreening; Salesforce reported prescreening coverage rose from 10% to 100%.
  - Source: `SRC-20260730-037`
  - Anchor: `01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt#L24`
  - Quote: "With Agentforce, Adecco’s prescreening coverage went from 10% to 100%."
- **F4** — Datasite replaced decisions that could not tolerate ambiguity with deterministic conditional logic.
  - Source: `SRC-20260730-037`
  - Anchor: `01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt#L28`
  - Quote: "find the decisions that couldn’t tolerate that ambiguity and replace them with conditional logic"
- **F5** — Salesforce reported that Datasite conversation failure fell from roughly 33% to 0.5%, sustained deflection averaged 82%, and CSAT was 4.8 out of 5.
  - Source: `SRC-20260730-037`
  - Anchor: `01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt#L30`
  - Quote: "Conversation failure rate dropped from roughly 33% to about 0.5%. Deflection climbed from the low 60s to a sustained average of 82%, running between 81% and 84% week to week. CSAT held at 4.8 out of 5, matching the performance of the live human support team."
- **F6** — Indeed was reported to operate four production Agentforce use cases.
  - Source: `SRC-20260730-037`
  - Anchor: `01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt#L33`
  - Quote: "Indeed runs Agentforce across four production use cases:"
- **F7** — Indeed's engineers were reported to deploy through APIs and a CLI while all agents used a shared preprocessed data layer.
  - Source: `SRC-20260730-037`
  - Anchor: `01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt#L34`
  - Quote: "Indeed’s engineers build through APIs and a CLI."
- **F8** — SharkNinja combined daily frontline stress testing with weekly conversation engineering.
  - Source: `SRC-20260730-037`
  - Anchor: `01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt#L40`
  - Quote: "The company also runs weekly conversation engineering meetings and structured learning sessions after every major iteration."
- **F9** — Salesforce reported SharkNinja's Digital Concierge had handled more than 250,000 conversations.
  - Source: `SRC-20260730-037`
  - Anchor: `01_Inbox/_assets/SRC-20260730-037/20260729233642-db03e4a15427.html.extracted.txt#L40`
  - Quote: "The Digital Concierge has now handled more than 250,000 conversations."

## Inferences

- The common production pattern is bounded agency layered on curated data, deterministic controls, human escalation and continuous evaluation.
- Named deployments span customer service, recruiting, M&A, IT and sales, showing breadth without proving an industry-wide success rate.
- Incumbent enterprise platforms can use their data and workflow position to distribute agents, but customers still perform material implementation work.

## Research judgment

The cases meet the threshold for named, verifiable customer deployments and provide useful scope and outcome indicators. They do not constitute independent validation of Salesforce because all five were selected and reported by its product marketing team, with incomplete metric definitions. They are suitable as B-grade case evidence and a follow-up list, not as proof of general Agentforce economics.

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| THS-001 | contextual | Agents took over meaningful task volume, but the cases retained human transfers, curated knowledge, conventional portals, scripts and operational interfaces. | 0.00, pending human review |
| THS-002 | supporting | Data preparation, shared context, deterministic logic and continuous evaluation repeatedly appear as production prerequisites. | 0.00, pending human review |
| THS-004 | contextual | The cases show an incumbent platform distributing agents into existing customer workflows, but do not disclose customer economics or competitive alternatives. | 0.00, pending human review |

## Source independence

| Group | Sources | Treatment |
|---|---|---|
| IG-01 | SRC-20260730-037 | independent root |

## Alternative explanations

- The reported gains may reflect selection of successful customers and favorable periods.
- Customer implementation practices rather than platform differentiation may drive the outcomes.
- Some reported coverage and deflection may shift complex work to humans rather than reduce total workload.

## Unknowns

- Measurement windows, sample sizes and consistent metric definitions are not disclosed.
- Customer implementation cost, subscription price and payback are unknown.
- Comparable outcomes on competing platforms are not provided.

## Follow-up indicators

- Seek direct customer disclosures from at least two of the five organizations.
- Track total cost per resolved task including human escalation and implementation labor.
- Compare production outcomes across Agentforce and competing control layers.
