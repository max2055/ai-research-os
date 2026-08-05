---
id: EVT-20250713-024
type: event
title: "Repository benchmark expansion finds large distribution and success-rate differences"
created_at: 2026-07-29
updated_at: '2026-07-30'
schema_version: 1
project_ids: [PRJ-002]
status: active
review_status: reviewed
event_date: 2025-07-13
source_ids: [SRC-20260729-032]
companies: []
technologies: [DEV-EVALUATION, DEV-AGENT-FRAMEWORK]
products: []
thesis_links: [THS-007]
confidence: 0.72
generation_method: structured
generation_fingerprint: 8022cf554688db3bc80e2688b82a51b03cf23fa267b54d8dd3e893bd77502b85
citation_anchors:
- fact_id: F1
  source_id: SRC-20260729-032
  asset_path: "01_Inbox/_assets/SRC-20260729-032/20260729160429-0993040b7eda.html.extracted.txt"
  locator: L13
  quote: "Code Agent development is an extremely active research area, where a reliable performance metric is critical for tracking progress and guiding new developments. This demand is underscored by the meteoric rise in popularity of SWE-Bench – a benchmark that challenges code agents to generate patches addressing GitHub issues given the full repository as context. The correctness of generated patches is then evaluated by executing a human-written test suite extracted from the repository after the issue’s resolution. However, constructing benchmarks like SWE-Bench requires substantial manual effort to set up historically accurate execution environments for testing. Crucially, this severely limits the number of considered repositories, e.g., just 12 for SWE-Bench. Considering so few repositories, selected for their popularity runs the risk of leading to a distributional mismatch, i.e., the measured performance may not be representative of real-world scenarios running the riks of misguiding development efforts. In this work, we address this challenge and introduce SetUpAgent, a fully automated system capable of historically accurate dependency setup, test execution, and result parsing. Using SetUpAgent, we generate two new datasets: (i) SWEE-Bench an extended version of SWE-Bench encompassing hundreds of repositories, and (ii) SWA-Bench a benchmark focusing on applications rather than libraries. Comparing these datasets to SWE-Bench with respect to their characteristics and code agent performance, we find significant distributional differences, including lower issue description quality and detail level, higher fix complexity, and most importantly up to 60% lower agent success rates."
  quote_sha256: 370b54f59249172c2fe0abac60304a4e723ef745e98dbe917c35025365e83411
- fact_id: F2
  source_id: SRC-20260729-032
  asset_path: "01_Inbox/_assets/SRC-20260729-032/20260729160429-0993040b7eda.html.extracted.txt"
  locator: L13
  quote: "Comparing these datasets to SWE-Bench with respect to their characteristics and code agent performance, we find significant distributional differences, including lower issue description quality and detail level, higher fix complexity, and most importantly up to 60% lower agent success rates."
  quote_sha256: 6e61c80b5d2b7e32411e296fb14d28f3838f56534c1a411d8964a14fd56bdb8c
source_independence_groups: [["SRC-20260729-032"]]
tags: [APP-CODING, MAT-RESEARCH, EV-TECHNOLOGY]
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

- **F1** — The ICML paper states that SWE-Bench covers 12 repositories and warns that this may create distribution mismatch.
  - Source: `SRC-20260729-032`
  - Anchor: `01_Inbox/_assets/SRC-20260729-032/20260729160429-0993040b7eda.html.extracted.txt#L13`
  - Quote: "Code Agent development is an extremely active research area, where a reliable performance metric is critical for tracking progress and guiding new developments. This demand is underscored by the meteoric rise in popularity of SWE-Bench – a benchmark that challenges code agents to generate patches addressing GitHub issues given the full repository as context. The correctness of generated patches is then evaluated by executing a human-written test suite extracted from the repository after the issue’s resolution. However, constructing benchmarks like SWE-Bench requires substantial manual effort to set up historically accurate execution environments for testing. Crucially, this severely limits the number of considered repositories, e.g., just 12 for SWE-Bench. Considering so few repositories, selected for their popularity runs the risk of leading to a distributional mismatch, i.e., the measured performance may not be representative of real-world scenarios running the riks of misguiding development efforts. In this work, we address this challenge and introduce SetUpAgent, a fully automated system capable of historically accurate dependency setup, test execution, and result parsing. Using SetUpAgent, we generate two new datasets: (i) SWEE-Bench an extended version of SWE-Bench encompassing hundreds of repositories, and (ii) SWA-Bench a benchmark focusing on applications rather than libraries. Comparing these datasets to SWE-Bench with respect to their characteristics and code agent performance, we find significant distributional differences, including lower issue description quality and detail level, higher fix complexity, and most importantly up to 60% lower agent success rates."
- **F2** — The paper reports up to 60% lower agent success rates on newly generated datasets with different repository and task characteristics.
  - Source: `SRC-20260729-032`
  - Anchor: `01_Inbox/_assets/SRC-20260729-032/20260729160429-0993040b7eda.html.extracted.txt#L13`
  - Quote: "Comparing these datasets to SWE-Bench with respect to their characteristics and code agent performance, we find significant distributional differences, including lower issue description quality and detail level, higher fix complexity, and most importantly up to 60% lower agent success rates."

## Inferences

- Headline benchmark performance may not transfer to a broader distribution of repositories and application tasks.
- Environment reconstruction and evaluation design are part of the measurement infrastructure needed to compare coding agents.

## Research judgment

This peer-reviewed benchmark paper is strong evidence of an evaluation-distribution problem. It does not directly prove commercial value capture by evaluation vendors, and its reported maximum performance gap should not be treated as an average production penalty.

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| THS-007 | supporting | The benchmark distribution gap supports the importance of evaluation infrastructure tailored to representative repositories and tasks. | 0.00, pending human review |

## Source independence

| Group | Sources | Treatment |
|---|---|---|
| IG-01 | SRC-20260729-032 | independent root |

## Alternative explanations

- Future general-purpose benchmarks may reduce the need for proprietary evaluation layers.
- The performance gap may narrow quickly with newer models or better agent scaffolds.

## Unknowns

- Production defect rates and economic outcomes are not measured.
- It is unknown how much of the gap comes from repository selection, issue quality, environment setup or agent design.

## Follow-up indicators

- Track performance dispersion across repository types, applications and private codebases.
- Compare benchmark results with production merge, rollback and intervention rates.
