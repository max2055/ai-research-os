---
id: EVT-20260224-023
type: event
title: "METR says its later developer-productivity experiment has severe selection limits"
created_at: 2026-07-29
updated_at: '2026-07-30'
schema_version: 1
project_ids: [PRJ-002]
status: active
review_status: reviewed
event_date: 2026-02-24
source_ids: [SRC-20260729-031]
companies: []
technologies: [DEV-EVALUATION, DEV-AGENT-FRAMEWORK]
products: []
thesis_links: [THS-006, THS-008]
confidence: 0.70
generation_method: structured
generation_fingerprint: 6f86e97a4f53dea38b68431f5fec8ed117a538f45ea2f88190e591273bff76f0
citation_anchors:
- fact_id: F1
  source_id: SRC-20260729-031
  asset_path: "01_Inbox/_assets/SRC-20260729-031/20260729160427-86b15db4c78d.html.extracted.txt"
  locator: L47
  quote: "Unfortunately, given participant feedback and surveys, we believe that the data from our new experiment gives us an unreliable signal of the current productivity effect of AI tools. The primary reason is that we have observed a significant increase in developers choosing not to participate in the study because they do not wish to work without AI, which likely biases downwards our estimate of AI-assisted speedup. We additionally believe there have been selection effects due to a lower pay rate (we reduced the pay from $150/hr to $50/hr), and that our measurements of time-spent on each task are unreliable for the fraction of developers who use multiple AI agents concurrently."
  quote_sha256: 9d40d0f9eff659ebb2fd806b2ff4b927dff2e822c9ad24f22a418e3ed30728bd
- fact_id: F2
  source_id: SRC-20260729-031
  asset_path: "01_Inbox/_assets/SRC-20260729-031/20260729160427-86b15db4c78d.html.extracted.txt"
  locator: L48
  quote: "Based on conversations with study participants, we believe it is likely that developers are more sped up from AI tools now — in early 2026 — compared to our estimates from early 2025. However, because of the selection effects in our experiment, our data is only very weak evidence for the size of this increase."
  quote_sha256: bd3e29788794195ae07cb6953e8fa0a4abb9f2ebacc0ddfe9ff67364f7cea4aa
- fact_id: F3
  source_id: SRC-20260729-031
  asset_path: "01_Inbox/_assets/SRC-20260729-031/20260729160427-86b15db4c78d.html.extracted.txt"
  locator: L49
  quote: "Our raw results show some evidence for speedup. Our early 2025 study found the use of AI causes tasks to take 19% longer, with a confidence interval between +2% and +39%. For the subset of the original developers who participated in the later study, we now estimate a speedup of -18% with a confidence interval between -38% and +9%. Among newly-recruited developers the estimated speedup is -4%, with a confidence interval between -15% and +9%."
  quote_sha256: 9edb1120c28d91c4cd66dd063b8a443101edef8605361a7f20831f10328f8920
- fact_id: F4
  source_id: SRC-20260729-031
  asset_path: "01_Inbox/_assets/SRC-20260729-031/20260729160427-86b15db4c78d.html.extracted.txt"
  locator: L57
  quote: "Developers have become more selective in which tasks they submit. When surveyed, 30% to 50% of developers told us that they were choosing not to submit some tasks because they did not want to do them without AI. This implies we are systematically missing tasks which have high expected uplift from AI."
  quote_sha256: 8335ce97162db1cd6d3a0087b1135251965d56b2a3d6bda85ac528f393b6c052
source_independence_groups: [["SRC-20260729-031"]]
tags: [APP-CODING, MAT-RESEARCH, EV-TECHNOLOGY]
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

- **F1** — METR says nonparticipation, pay-rate changes and concurrent-agent measurement make its later experiment an unreliable signal.
  - Source: `SRC-20260729-031`
  - Anchor: `01_Inbox/_assets/SRC-20260729-031/20260729160427-86b15db4c78d.html.extracted.txt#L47`
  - Quote: "Unfortunately, given participant feedback and surveys, we believe that the data from our new experiment gives us an unreliable signal of the current productivity effect of AI tools. The primary reason is that we have observed a significant increase in developers choosing not to participate in the study because they do not wish to work without AI, which likely biases downwards our estimate of AI-assisted speedup. We additionally believe there have been selection effects due to a lower pay rate (we reduced the pay from $150/hr to $50/hr), and that our measurements of time-spent on each task are unreliable for the fraction of developers who use multiple AI agents concurrently."
- **F2** — METR believes developers are likely more sped up in early 2026 than in early 2025, but calls its evidence on the size of the increase very weak.
  - Source: `SRC-20260729-031`
  - Anchor: `01_Inbox/_assets/SRC-20260729-031/20260729160427-86b15db4c78d.html.extracted.txt#L48`
  - Quote: "Based on conversations with study participants, we believe it is likely that developers are more sped up from AI tools now — in early 2026 — compared to our estimates from early 2025. However, because of the selection effects in our experiment, our data is only very weak evidence for the size of this increase."
- **F3** — METR reports later point estimates whose confidence intervals include no speedup.
  - Source: `SRC-20260729-031`
  - Anchor: `01_Inbox/_assets/SRC-20260729-031/20260729160427-86b15db4c78d.html.extracted.txt#L49`
  - Quote: "Our raw results show some evidence for speedup. Our early 2025 study found the use of AI causes tasks to take 19% longer, with a confidence interval between +2% and +39%. For the subset of the original developers who participated in the later study, we now estimate a speedup of -18% with a confidence interval between -38% and +9%. Among newly-recruited developers the estimated speedup is -4%, with a confidence interval between -15% and +9%."
- **F4** — Between 30% and 50% of surveyed developers said they withheld some tasks because they did not want to perform them without AI.
  - Source: `SRC-20260729-031`
  - Anchor: `01_Inbox/_assets/SRC-20260729-031/20260729160427-86b15db4c78d.html.extracted.txt#L57`
  - Quote: "Developers have become more selective in which tasks they submit. When surveyed, 30% to 50% of developers told us that they were choosing not to submit some tasks because they did not want to do them without AI. This implies we are systematically missing tasks which have high expected uplift from AI."

## Inferences

- As agent use becomes embedded in work, randomized task studies may systematically exclude high-uplift users and tasks.
- The direction of productivity change may be improving, but this source does not reliably quantify its magnitude.

## Research judgment

This update is valuable because it weakens both a simple extrapolation of the 2025 slowdown and an aggressive claim of current speedup. The appropriate conclusion is measurement uncertainty and task heterogeneity, not a midpoint estimate.

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| THS-006 | contextual | The update suggests agentic workflows may be changing task selection while making aggregate productivity harder to estimate. | 0.00, pending human review |
| THS-008 | contextual | Wide intervals and selection effects mean current economic uplift cannot be reliably inferred from this experiment. | 0.00, pending human review |

## Source independence

| Group | Sources | Treatment |
|---|---|---|
| IG-01 | SRC-20260729-031 | independent root |

## Alternative explanations

- The observed participation problem may reflect the lower pay rate rather than large AI productivity benefits.
- Concurrent agent use may add output beyond task-time measures but may also increase review and coordination costs.

## Unknowns

- The productivity effect for developers and tasks excluded from the experiment is unobserved.
- Quality-adjusted value and cost across concurrent agents are not measured.

## Follow-up indicators

- Track redesigned studies that accommodate task selection and concurrent agents.
- Seek production telemetry linking agent usage, task mix, quality and total labor time.
