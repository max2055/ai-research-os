---
id: EVT-20250729-020
type: event
title: "Developer survey shows broad AI-tool interest but limited agent use and weak trust"
created_at: 2026-07-29
updated_at: '2026-07-30'
schema_version: 1
project_ids: [PRJ-002]
status: active
review_status: reviewed
event_date: 2025-07-29
source_ids: [SRC-20260729-028]
companies: []
technologies: [DEV-AGENT-FRAMEWORK]
products: []
thesis_links: [THS-006, THS-007]
confidence: 0.60
generation_method: structured
generation_fingerprint: 9c8bdf2604cbcd7434070cd747ae927606224269d8b1ccd8501191de7a564a05
citation_anchors:
- fact_id: F1
  source_id: SRC-20260729-028
  asset_path: "01_Inbox/_assets/SRC-20260729-028/20260729160419-660232ced40e.html.extracted.txt"
  locator: L8
  quote: "New York City– July 29, 2025 – Stack Overflow today announced the results of its 2025 Developer Survey, its definitive report on the state of software development. In its fifteenth year, Stack Overflow received over 49,000 responses from 177 countries across 62 questions focused on 314 different technologies; including new focus on AI agent tools, LLMs and community platforms. This annual Developer Survey provides a crucial snapshot into the needs of the global developer community, focusing on the tools and technologies they use or want to learn more about."
  quote_sha256: 595bc37a1596cbf463affd5aba4f0a3c843e650bd5956695ef30da2a6bd71588
- fact_id: F2
  source_id: SRC-20260729-028
  asset_path: "01_Inbox/_assets/SRC-20260729-028/20260729160419-660232ced40e.html.extracted.txt"
  locator: L10
  quote: "For the third year in a row, our survey demonstrated an increase in the number of developers using AI tools year over year, with 84% saying they use or plan to use AI tools in their development process, up from 76% in 2024. However, 46% of developers said they don't trust the accuracy of the output from AI tools, a significant increase from 31% last year.This year’s Developer Survey includes an expanded section dedicated to the growing landscape of artificial intelligence, with 15 new questions to glean insights on top usage and utility questions for AI-enabled technology and AI agent tools, AI's impact on how developers work, and whether developers have engaged in \"vibe coding\" in the last year."
  quote_sha256: e600351ec16c0fa0043921a2ff0d2001448968eecdf0a946739674132785f2f1
- fact_id: F3
  source_id: SRC-20260729-028
  asset_path: "01_Inbox/_assets/SRC-20260729-028/20260729160419-660232ced40e.html.extracted.txt"
  locator: L16
  quote: "AI agents are not being used by the majority of developers, with only 31% using them currently, 17% planning to, and 38% of respondents not planning to use AI agents. However, for those developers who have used AI agents at work, 69% agree they have experienced an increase in productivity."
  quote_sha256: fb20b6048b49e08ca8f95df90391e02fdbfafa98f4bb6104cbde693b8a3068f3
source_independence_groups: [["SRC-20260729-028"]]
tags: [APP-CODING, MAT-PILOT, EV-CUSTOMER]
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

- **F1** — Stack Overflow reports more than 49,000 responses from 177 countries in its 2025 survey.
  - Source: `SRC-20260729-028`
  - Anchor: `01_Inbox/_assets/SRC-20260729-028/20260729160419-660232ced40e.html.extracted.txt#L8`
  - Quote: "New York City– July 29, 2025 – Stack Overflow today announced the results of its 2025 Developer Survey, its definitive report on the state of software development. In its fifteenth year, Stack Overflow received over 49,000 responses from 177 countries across 62 questions focused on 314 different technologies; including new focus on AI agent tools, LLMs and community platforms. This annual Developer Survey provides a crucial snapshot into the needs of the global developer community, focusing on the tools and technologies they use or want to learn more about."
- **F2** — The survey reports 84% use or plan to use AI tools, while 46% distrust AI-output accuracy.
  - Source: `SRC-20260729-028`
  - Anchor: `01_Inbox/_assets/SRC-20260729-028/20260729160419-660232ced40e.html.extracted.txt#L10`
  - Quote: "For the third year in a row, our survey demonstrated an increase in the number of developers using AI tools year over year, with 84% saying they use or plan to use AI tools in their development process, up from 76% in 2024. However, 46% of developers said they don't trust the accuracy of the output from AI tools, a significant increase from 31% last year.This year’s Developer Survey includes an expanded section dedicated to the growing landscape of artificial intelligence, with 15 new questions to glean insights on top usage and utility questions for AI-enabled technology and AI agent tools, AI's impact on how developers work, and whether developers have engaged in \"vibe coding\" in the last year."
- **F3** — The survey reports 31% current agent use, 17% planned use and 38% not planning to use agents; 69% of workplace agent users agreed productivity increased.
  - Source: `SRC-20260729-028`
  - Anchor: `01_Inbox/_assets/SRC-20260729-028/20260729160419-660232ced40e.html.extracted.txt#L16`
  - Quote: "AI agents are not being used by the majority of developers, with only 31% using them currently, 17% planning to, and 38% of respondents not planning to use AI agents. However, for those developers who have used AI agents at work, 69% agree they have experienced an increase in productivity."

## Inferences

- Interest in AI development tools is materially broader than current use of agentic workflows.
- Reported productivity among users coexists with a substantial trust and validation problem.

## Research judgment

The survey is useful for adoption and perception, not for causal productivity measurement. Self-selection, question wording and the difference between general AI tools and agents limit any inference about realized economic value.

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| THS-006 | contextual | The data shows an early adoption gap: agent use is not yet a majority behavior despite broad AI-tool interest. | 0.00, pending human review |
| THS-007 | supporting | High distrust of AI-output accuracy is consistent with validation and governance remaining important parts of the product stack. | 0.00, pending human review |

## Source independence

| Group | Sources | Treatment |
|---|---|---|
| IG-01 | SRC-20260729-028 | independent root |

## Alternative explanations

- Distrust may decline rapidly as models improve and users gain experience.
- Current non-use may reflect availability and procurement timing rather than weak demand.

## Unknowns

- The press release excerpt does not provide response weighting or nonresponse-bias analysis.
- Self-reported productivity is not linked to objective task, quality or cost metrics.

## Follow-up indicators

- Track repeated survey measures of current agent use and trust.
- Compare self-reported productivity with controlled task and production-quality outcomes.
