---
id: RPT-20260730-ai-coding-agent-value-chain-v0-1
type: report
title: "AI Coding Agent Value Chain Pilot Report v0.1"
created_at: 2026-07-30
updated_at: '2026-07-30'
schema_version: 1
project_ids: [PRJ-002]
status: final
review_status: reviewed
report_type: topic
period_start: 2025-07-10
period_end: 2026-07-30
thesis_ids: [THS-006, THS-007, THS-008]
evidence_ids: [EVT-20250710-022, EVT-20250713-024, EVT-20250729-020, EVT-20250820-016, EVT-20250923-021, EVT-20251002-017, EVT-20251106-018, EVT-20260224-023, EVT-20260406-019]
version: v0.1
supersedes:
superseded_by:
generation_method: structured
generation_fingerprint: 0b4387b7c29bb463b92fb4ebd8d0e276dd9f7e9895db554bf3ab3aec356dcfaf
baseline_snapshot:
tags: [APP-CODING, MAT-RESEARCH]
---

# AI Coding Agent Value Chain Pilot Report v0.1

> Structured synthesis from reviewed Evidence. Facts, inferences and judgments remain
> separated; approval does not convert this Report into an investment recommendation.

## One-sentence conclusion

Nine reviewed Events support the emergence of an asynchronous coding-task layer and
the importance of context, evaluation and workflow infrastructure, while heterogeneous
productivity results and undisclosed unit economics prevent a durable value-capture
or investment conclusion.

## Research question and scope

This topic Report covers 2025-07-10 through 2026-07-30 and asks where AI Coding
Agents may redistribute software-development value. It uses only the nine explicitly
selected reviewed Event IDs and preserves vendor, survey, sample-size and
external-validity limits.

## Facts

### EVT-20250710-022 — METR randomized trial finds early-2025 AI tools slowed experienced developers

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

### EVT-20250713-024 — Repository benchmark expansion finds large distribution and success-rate differences

- **F1** — The ICML paper states that SWE-Bench covers 12 repositories and warns that this may create distribution mismatch.
  - Source: `SRC-20260729-032`
  - Anchor: `01_Inbox/_assets/SRC-20260729-032/20260729160429-0993040b7eda.html.extracted.txt#L13`
  - Quote: "Code Agent development is an extremely active research area, where a reliable performance metric is critical for tracking progress and guiding new developments. This demand is underscored by the meteoric rise in popularity of SWE-Bench – a benchmark that challenges code agents to generate patches addressing GitHub issues given the full repository as context. The correctness of generated patches is then evaluated by executing a human-written test suite extracted from the repository after the issue’s resolution. However, constructing benchmarks like SWE-Bench requires substantial manual effort to set up historically accurate execution environments for testing. Crucially, this severely limits the number of considered repositories, e.g., just 12 for SWE-Bench. Considering so few repositories, selected for their popularity runs the risk of leading to a distributional mismatch, i.e., the measured performance may not be representative of real-world scenarios running the riks of misguiding development efforts. In this work, we address this challenge and introduce SetUpAgent, a fully automated system capable of historically accurate dependency setup, test execution, and result parsing. Using SetUpAgent, we generate two new datasets: (i) SWEE-Bench an extended version of SWE-Bench encompassing hundreds of repositories, and (ii) SWA-Bench a benchmark focusing on applications rather than libraries. Comparing these datasets to SWE-Bench with respect to their characteristics and code agent performance, we find significant distributional differences, including lower issue description quality and detail level, higher fix complexity, and most importantly up to 60% lower agent success rates."
- **F2** — The paper reports up to 60% lower agent success rates on newly generated datasets with different repository and task characteristics.
  - Source: `SRC-20260729-032`
  - Anchor: `01_Inbox/_assets/SRC-20260729-032/20260729160429-0993040b7eda.html.extracted.txt#L13`
  - Quote: "Comparing these datasets to SWE-Bench with respect to their characteristics and code agent performance, we find significant distributional differences, including lower issue description quality and detail level, higher fix complexity, and most importantly up to 60% lower agent success rates."

### EVT-20250729-020 — Developer survey shows broad AI-tool interest but limited agent use and weak trust

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

### EVT-20250820-016 — Coding agent commercial plans combine subscriptions with usage meters

- **F1** — GitHub announced that a Copilot coding-agent session consumes exactly one premium request.
  - Source: `SRC-20260729-021`
  - Anchor: `01_Inbox/_assets/SRC-20260729-021/20260729160202-e8d67ae4d1ba.html.extracted.txt#L29`
  - Quote: "Starting 19:00 UTC (12pm Pacific / 3pm Eastern) today, July 10th, we’re making our pricing simpler and more predictable. Copilot coding agent will now use exactly one Copilot premium request per session."
- **F2** — GitHub stated that Actions-minute consumption still varies with task duration even when premium-request consumption is fixed.
  - Source: `SRC-20260729-021`
  - Anchor: `01_Inbox/_assets/SRC-20260729-021/20260729160202-e8d67ae4d1ba.html.extracted.txt#L35`
  - Quote: "Note: The agent runs on GitHub Actions. While premium request usage is now fixed, the GitHub Actions minutes used will still vary depending on how long Copilot needs to complete your task."
- **F3** — Anthropic said business seats include usage and can add usage at standard API rates subject to administrator-set limits.
  - Source: `SRC-20260729-022`
  - Anchor: `01_Inbox/_assets/SRC-20260729-022/20260729160218-c182ce109975.html.extracted.txt#L20`
  - Quote: "Claude seats include enough usage for a typical workday, but for times when your teams need access to more intelligence and additional conversations with Claude–admins can enable extra usage for individual users at standard API rates. Admins have control over the maximum amount a user can spend with extra usage to ensure that users get flexibility and admins get predictable billing."
- **F4** — Cursor described Pro as including a monthly frontier-model credit pool with additional usage available at cost.
  - Source: `SRC-20260729-024`
  - Anchor: `01_Inbox/_assets/SRC-20260729-024/20260729160222-0b74ed3c8035.html.extracted.txt#L49-L52`
  - Quote: "The new Cursor Pro plan gives you:\nUnlimited usage of Tab and models in Auto\n$20 of frontier model usage per month at API pricing\nAn option to purchase more frontier model usage at cost"

### EVT-20250923-021 — DORA frames AI-assisted development as an organizational amplifier

- **F1** — DORA's report landing page characterizes AI as amplifying existing organizational strengths and weaknesses.
  - Source: `SRC-20260729-029`
  - Anchor: `01_Inbox/_assets/SRC-20260729-029/20260729160420-6bb53c243fc6.html.extracted.txt#L39`
  - Quote: "The State of AI-assisted Software Development report reveals AI’s primary role is as an amplifier, magnifying an organization’s existing strengths and weaknesses. The greatest returns on AI investment come not from the tools themselves, but from a strategic focus on the underlying organizational system."

### EVT-20251002-017 — Cloud coding agents are packaged as asynchronous task-to-pull-request systems

- **F1** — GitHub describes developers delegating coding tasks to an agent that works in the background.
  - Source: `SRC-20260729-021`
  - Anchor: `01_Inbox/_assets/SRC-20260729-021/20260729160202-e8d67ae4d1ba.html.extracted.txt#L28`
  - Quote: "With GitHub Copilot coding agent, developers can tackle tech debt, fix bugs, and even implement new features at scale. Simply delegate tasks to Copilot, and let it work in the background while you focus on something else."
- **F2** — Google describes Jules as an asynchronous coding agent operating against repositories.
  - Source: `SRC-20260729-023`
  - Anchor: `01_Inbox/_assets/SRC-20260729-023/20260729160221-e3343dd1564a.html.extracted.txt#L25`
  - Quote: "You can now work with Jules directly in your command line. Jules is our asynchronous coding agent that integrates directly with your existing repositories, understands the full context of your project, and performs tasks such as writing tests, building new features, providing audio changelogs, fixing bugs, and bumping dependency versions."
- **F3** — Google says a Jules task runs in a temporary remote VM and returns a pull request.
  - Source: `SRC-20260729-023`
  - Anchor: `01_Inbox/_assets/SRC-20260729-023/20260729160221-e3343dd1564a.html.extracted.txt#L29`
  - Quote: "Jules already runs in the background, powering tasks in remote VMs and synching with your repos. When you start a task, it spins up a temporary VM, does the work there, and sends back a pull request. Nothing runs until you ask it to. The command line gives you even more direct control and visibility. It makes Jules programmable, scriptable, and customizable. You can integrate it into your own automations, or just type a few quick commands to steer Jules in real time."
- **F4** — OpenAI states that each Codex agent runs in its own cloud container without internet access after setup.
  - Source: `SRC-20260729-025`
  - Anchor: `01_Inbox/_assets/SRC-20260729-025/20260729160339-066d1d99a6c8.pdf.extracted.txt#L9-L14`
  - Quote: "Users can ask Codex to perform coding tasks or to answer questions about a codebase. Each\nagent runs in its own cloud container with no internet access. The container is preloaded with\nthe user’s code and a development environment defined by the user, including any dependencies,\nconfiguration, or tooling they specify. After setup, internet access is disabled and the model\ntrajectory begins. Within that environment, Codex can read and edit files, as well as execute\ncommands including tests, linters, and type checkers."

### EVT-20251106-018 — Spotify reports production use of an internal background coding-agent stack

- **F1** — Spotify retained its existing repository targeting, pull-request, review and merge infrastructure while replacing deterministic transformation scripts with an agent.
  - Source: `SRC-20260729-026`
  - Anchor: `01_Inbox/_assets/SRC-20260729-026/20260729160341-8a8e2e9428f0.html.extracted.txt#L23`
  - Quote: "We started with the part of the process that needed the most help: the declaration of the code transformation itself. We replaced deterministic migration scripts with an agent that takes instructions from a prompt. All the surrounding Fleet Management infrastructure — targeting repositories, opening pull requests, getting reviews, and merging into production — remains exactly the same."
- **F2** — Spotify built an internal CLI with formatting, linting, LLM judging, logging and tracing, and designed it to switch agents and models.
  - Source: `SRC-20260729-026`
  - Anchor: `01_Inbox/_assets/SRC-20260729-026/20260729160341-8a8e2e9428f0.html.extracted.txt#L25`
  - Quote: "Instead of adopting an off-the-shelf coding agent as it is, we decided to build a small internal CLI. This CLI can delegate executing a prompt to an agent, run custom formatting and linting tasks using local Model Context Protocol (MCP), evaluate a diff using LLMs as a judge, upload logs to Google Cloud Platform (GCP), and capture traces in MLflow. Crucially, having that CLI allows us to seamlessly switch between different agents and LLMs. In the fast-moving environment that is GenAI, being flexible and pluggable this way has already allowed us to swap out pieces multiple times, giving our users a preconfigured and well-integrated tool out of the box, without exposing them to the nitty-gritty details."
- **F3** — Spotify reports that teams merged more than 1,500 agent-generated pull requests into production.
  - Source: `SRC-20260729-026`
  - Anchor: `01_Inbox/_assets/SRC-20260729-026/20260729160341-8a8e2e9428f0.html.extracted.txt#L27`
  - Quote: "We saw an immediate need for this type of product internally. We were codeveloping the tooling alongside early adopters who applied it to their in-flight migrations. To date, our agents have generated more than 1,500 pull requests that teams across Spotify have merged into our production codebase. And not trivial changes, either — we’re now starting to tackle changes such as:"
- **F4** — Spotify identifies performance, output unpredictability, validation, safety, sandboxing and compute expense as remaining trade-offs.
  - Source: `SRC-20260729-026`
  - Anchor: `01_Inbox/_assets/SRC-20260729-026/20260729160341-8a8e2e9428f0.html.extracted.txt#L42`
  - Quote: "But coding agents come with an interesting set of trade-offs. Performance is a key consideration, as agents can take a long time to produce a result, and their output can be unpredictable. This creates a need for new validation and quality control mechanisms. Beyond performance and predictability, we also have to consider safety and cost. We need robust guardrails and sandboxing to ensure agents operate as intended, all while managing the significant computational expense of running LLMs at scale."

### EVT-20260224-023 — METR says its later developer-productivity experiment has severe selection limits

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

### EVT-20260406-019 — Meta reports context infrastructure reducing coding-agent exploration

- **F1** — Meta says it generated 59 context files for a 4,100-file pipeline and measured 40% fewer tool calls in preliminary tests.
  - Source: `SRC-20260729-027`
  - Anchor: `01_Inbox/_assets/SRC-20260729-027/20260729160342-c4c3746bda38.html.extracted.txt#L36`
  - Quote: "We fixed this by building a pre-compute engine: a swarm of 50+ specialized AI agents that systematically read every file and produced 59 concise context files encoding tribal knowledge that previously lived only in engineers’ heads. The result: AI agents now have structured navigation guides for 100% of our code modules (up from 5%, covering all 4,100+ files across three repositories). We also documented 50+ “non-obvious patterns,” or underlying design choices and relationships not immediately apparent from the code, and preliminary tests show 40% fewer AI agent tool calls per task. The system works with most leading models because the knowledge layer is model-agnostic."
- **F2** — Meta reports that agents without this context sometimes produced code that compiled but was subtly wrong.
  - Source: `SRC-20260729-027`
  - Anchor: `01_Inbox/_assets/SRC-20260729-027/20260729160342-c4c3746bda38.html.extracted.txt#L41`
  - Quote: "Without this context, agents would guess, explore, guess again and often produce code that compiled but was subtly wrong."
- **F3** — The reported tool-call reduction was based on preliminary tests covering six tasks.
  - Source: `SRC-20260729-027`
  - Anchor: `01_Inbox/_assets/SRC-20260729-027/20260729160342-c4c3746bda38.html.extracted.txt#L86`
  - Quote: "In preliminary tests on six tasks against our pipeline, agents with pre-computed context used roughly 40% fewer tool calls and tokens per task. Complex workflow guidance that previously required ~two days of research and consulting with engineers now completes in ~30 minutes."
- **F4** — Meta explicitly notes contrary academic findings in familiar open-source repositories.
  - Source: `SRC-20260729-027`
  - Anchor: `01_Inbox/_assets/SRC-20260729-027/20260729160342-c4c3746bda38.html.extracted.txt#L89`
  - Quote: "Recent academic research found that AI-generated context files actually decreased agent success rates on well-known open-source Python repositories. This finding deserves serious consideration but it has a limitation: It was evaluated on codebases like Django and matplotlib that models already “know” from pretraining. In that scenario, context files are redundant noise."

## Inferences

- **EVT-20250710-022:** - At least in this early-2025 setting, perceived productivity and forecast productivity materially diverged from measured completion time. - Agent adoption and subjective satisfaction cannot be treated as sufficient evidence of economic productivity.

- **EVT-20250713-024:** - Headline benchmark performance may not transfer to a broader distribution of repositories and application tasks. - Environment reconstruction and evaluation design are part of the measurement infrastructure needed to compare coding agents.

- **EVT-20250729-020:** - Interest in AI development tools is materially broader than current use of agentic workflows. - Reported productivity among users coexists with a substantial trust and validation problem.

- **EVT-20250820-016:** - These three vendors expose different billing units, but all preserve a variable-usage component underneath or alongside a subscription. - Task- or session-level packaging may improve buyer predictability without eliminating model and compute cost sensitivity.

- **EVT-20250923-021:** - Realized AI-development value may depend on delivery systems, process quality and organizational capability rather than tool access alone. - A tool-level adoption metric can therefore diverge from enterprise-level value realization.

- **EVT-20251002-017:** - Multiple vendors converge on a task abstraction that couples repository context, isolated execution and pull-request delivery. - The value proposition extends beyond code completion toward delegated workflow execution.

- **EVT-20251106-018:** - In this deployment, organizational workflow and evaluation infrastructure remained important even as the code-transformation component became model-driven. - The internal abstraction layer reduced dependence on a single agent or model implementation.

- **EVT-20260224-023:** - As agent use becomes embedded in work, randomized task studies may systematically exclude high-uplift users and tasks. - The direction of productivity change may be improving, but this source does not reliably quantify its magnitude.

- **EVT-20260406-019:** - Context infrastructure may have more value in proprietary, cross-repository systems than in familiar open-source repositories represented in model training. - The result suggests that context quality and selective loading, not context volume alone, may determine value.

## Research judgment

- **EVT-20250710-022:** This is stronger causal evidence than vendor claims or surveys, but external validity is bounded by 16 experienced maintainers, their own mature repositories and early-2025 tools. It is a direct contradiction to universal productivity claims, not proof that later agents or other task types always slow developers.

- **EVT-20250713-024:** This peer-reviewed benchmark paper is strong evidence of an evaluation-distribution problem. It does not directly prove commercial value capture by evaluation vendors, and its reported maximum performance gap should not be treated as an average production penalty.

- **EVT-20250729-020:** The survey is useful for adoption and perception, not for causal productivity measurement. Self-selection, question wording and the difference between general AI tools and agents limit any inference about realized economic value.

- **EVT-20250820-016:** This is evidence that coding-agent monetization is experimenting with hybrid packaging, not evidence that any pricing model has durable margins. Vendor disclosures omit cohort-level gross margin, retention and realized cost-to-serve.

- **EVT-20250923-021:** This is a high-level conclusion from a primary research program, but the captured landing page does not expose the underlying sample, model or effect estimates. It should guide questions, not establish a causal claim by itself.

- **EVT-20251002-017:** The cross-vendor convergence supports treating asynchronous task execution as a distinct product layer. It does not establish that this layer captures durable value independently of model providers, repositories or developer platforms.

- **EVT-20251106-018:** This is a material production case because it reports merged output and describes the surrounding control stack. It remains a single-company engineering account without an independent audit, denominator, defect rate or fully specified cost baseline.

- **EVT-20260224-023:** This update is valuable because it weakens both a simple extrapolation of the 2025 slowdown and an aggressive claim of current speedup. The appropriate conclusion is measurement uncertainty and task heterogeneity, not a midpoint estimate.

- **EVT-20260406-019:** The case supports context as a potential control and efficiency layer, but its quantitative result is preliminary and based on six tasks. The source itself preserves a conflicting result from another setting, so generalization should remain low-confidence.

## Thesis assessment

| Thesis | Relationship | Evidence | Explanation |
|---|---|---|---|
| THS-006 | contradicting | EVT-20250710-022 | The result challenges the assumption that moving from assistance to delegated work automatically improves developer productivity. |
| THS-008 | contradicting | EVT-20250710-022 | A measured slowdown in a realistic task setting challenges favorable unit-economics assumptions based only on adoption or perceived time saving. |

No selected reviewed Event directly contradicts `THS-007`. This is a formal
no-result record for the pilot, not confirmation of the Thesis; the missing
counterevidence remains a research gap.
| THS-007 | supporting | EVT-20250713-024 | The benchmark distribution gap supports the importance of evaluation infrastructure tailored to representative repositories and tasks. |
| THS-006 | contextual | EVT-20250729-020 | The data shows an early adoption gap: agent use is not yet a majority behavior despite broad AI-tool interest. |
| THS-007 | supporting | EVT-20250729-020 | High distrust of AI-output accuracy is consistent with validation and governance remaining important parts of the product stack. |
| THS-008 | supporting | EVT-20250820-016 | The observed mix of seats, credits, sessions and infrastructure minutes is consistent with economics being shaped by both packaging and variable compute usage. |
| THS-007 | supporting | EVT-20250923-021 | The conclusion is consistent with complementary organizational and workflow systems determining value beyond the base coding tool. |
| THS-006 | supporting | EVT-20251002-017 | Three vendor implementations support the existence of an asynchronous task-to-pull-request layer above interactive code completion. |
| THS-007 | contextual | EVT-20251002-017 | The implementations make repository context, execution environments and validation surfaces part of the product boundary. |
| THS-006 | supporting | EVT-20251106-018 | The case demonstrates background agents integrated into an established task-to-review workflow at production scale. |
| THS-007 | supporting | EVT-20251106-018 | Spotify's pluggable CLI, evaluation, tracing and unchanged workflow infrastructure support the importance of the harness around the model. |
| THS-006 | contextual | EVT-20260224-023 | The update suggests agentic workflows may be changing task selection while making aggregate productivity harder to estimate. |
| THS-008 | contextual | EVT-20260224-023 | Wide intervals and selection effects mean current economic uplift cannot be reliably inferred from this experiment. |
| THS-007 | supporting | EVT-20260406-019 | The case directly attributes fewer tool calls and fewer subtle errors to a model-agnostic, quality-gated context layer. |

## Contradicting Evidence

| THS-006 | contradicting | EVT-20250710-022 | The result challenges the assumption that moving from assistance to delegated work automatically improves developer productivity. |
| THS-008 | contradicting | EVT-20250710-022 | A measured slowdown in a realistic task setting challenges favorable unit-economics assumptions based only on adoption or perceived time saving. |

## Source independence

| Group | Sources | Counting treatment |
|---|---|---|
| IG-01 | SRC-20260729-021 | independent |
| IG-02 | SRC-20260729-022 | independent |
| IG-03 | SRC-20260729-023 | independent |
| IG-04 | SRC-20260729-024 | independent |
| IG-05 | SRC-20260729-025 | independent |
| IG-06 | SRC-20260729-026 | independent |
| IG-07 | SRC-20260729-027 | independent |
| IG-08 | SRC-20260729-028 | independent |
| IG-09 | SRC-20260729-029 | independent |
| IG-10 | SRC-20260729-030 | independent |
| IG-11 | SRC-20260729-031 | independent |
| IG-12 | SRC-20260729-032 | independent |

## Contrarian view

- **EVT-20250710-022:** - Later models and agentic tools may perform materially better than the February–June 2025 tool frontier. - Experienced maintainers in familiar repositories may have less room for AI assistance than other developer cohorts.
- **EVT-20250713-024:** - Future general-purpose benchmarks may reduce the need for proprietary evaluation layers. - The performance gap may narrow quickly with newer models or better agent scaffolds.
- **EVT-20250729-020:** - Distrust may decline rapidly as models improve and users gain experience. - Current non-use may reflect availability and procurement timing rather than weak demand.
- **EVT-20250820-016:** - Hybrid pricing may be a transitional response to model-price volatility rather than a stable industry structure. - Vendors may subsidize usage for adoption, so list-price mechanics may not represent long-run unit economics.
- **EVT-20250923-021:** - The amplifier framing may aggregate heterogeneous findings and may not isolate coding agents from other AI tools. - Model capability improvements could reduce dependence on organizational maturity over time.
- **EVT-20251002-017:** - The shared architecture may be a temporary implementation pattern rather than a separately monetizable layer. - Repository platforms or foundation-model providers may absorb most of this functionality.
- **EVT-20251106-018:** - The reported success may depend on unusually standardized migration tasks and mature internal infrastructure. - The internal platform may be valuable only at Spotify's scale and may not imply an external software market.
- **EVT-20260224-023:** - The observed participation problem may reflect the lower pay rate rather than large AI productivity benefits. - Concurrent agent use may add output beyond task-time measures but may also increase review and coordination costs.
- **EVT-20260406-019:** - The improvement may reflect documentation of an unusually opaque proprietary pipeline rather than a reusable moat. - Equivalent gains might be achieved through conventional documentation or repository refactoring.

## Falsification conditions

The proposed interpretations should be weakened if production deployments remain
limited to narrow tasks, if quality-adjusted output does not improve after review and
rework, if repository context/evaluation becomes an undifferentiated bundled feature,
or if usage/task revenue does not cover inference, verification and support cost.

## Key indicators

- **EVT-20250710-022:** - Track replications using current agentic tools and larger developer samples. - Measure quality-adjusted output and total review/rework time, not completion time alone.
- **EVT-20250713-024:** - Track performance dispersion across repository types, applications and private codebases. - Compare benchmark results with production merge, rollback and intervention rates.
- **EVT-20250729-020:** - Track repeated survey measures of current agent use and trust. - Compare self-reported productivity with controlled task and production-quality outcomes.
- **EVT-20250820-016:** - Track changes in included credits, overage rates and task/session definitions. - Seek customer-level data on spend expansion, retention and realized engineering output.
- **EVT-20250923-021:** - Archive and inspect the full DORA report methodology and capability model. - Track whether deployment outcomes correlate with delivery-system maturity after controlling for tool choice.
- **EVT-20251002-017:** - Track task completion, human-intervention and pull-request merge rates. - Track whether repository and CI vendors bundle agent execution into existing plans.
- **EVT-20251106-018:** - Seek task denominators, rollback rates, review time and production incidents. - Track whether the internal orchestration and evaluation layer becomes standardized or commercially sourced.
- **EVT-20260224-023:** - Track redesigned studies that accommodate task selection and concurrent agents. - Seek production telemetry linking agent usage, task mix, quality and total labor time.
- **EVT-20260406-019:** - Seek controlled comparisons across proprietary and familiar open-source repositories. - Measure end-to-end success, maintenance cost and stale-context failure rates.

## Investment implications

The Evidence supports research prioritization only. Security selection still requires
valuation, expectations, unit economics and independently reviewed company evidence.

## Risks and unknowns

- **EVT-20250710-022:** - The result does not determine effects on code quality, documentation, learning or longer-horizon output. - The effect for autonomous background agents and greenfield tasks is not established.
- **EVT-20250713-024:** - Production defect rates and economic outcomes are not measured. - It is unknown how much of the gap comes from repository selection, issue quality, environment setup or agent design.
- **EVT-20250729-020:** - The press release excerpt does not provide response weighting or nonresponse-bias analysis. - Self-reported productivity is not linked to objective task, quality or cost metrics.
- **EVT-20250820-016:** - Gross margin and cost-to-serve by task complexity are not disclosed. - The share of users exceeding included usage and their retention is unknown.
- **EVT-20250923-021:** - The captured page does not provide the report's sample, statistical method or measured effect sizes. - The contribution of specific context, evaluation and sandbox components is not separated.
- **EVT-20251002-017:** - Comparable task success, intervention and merge rates across vendors are unavailable. - The share of developer work suitable for asynchronous delegation is unknown.
- **EVT-20251106-018:** - The total attempted-task denominator, defect rate and human-review effort are not disclosed. - The 60–90% claimed time saving is not independently verified and its measurement method is not described in the excerpt.
- **EVT-20260224-023:** - The productivity effect for developers and tasks excluded from the experiment is unobserved. - Quality-adjusted value and cost across concurrent agents are not measured.
- **EVT-20260406-019:** - Task selection, baseline models, success criteria and variance across the six tasks are not fully disclosed. - The engineering and inference cost of creating and maintaining the context layer is unknown.

## Next research actions

- **EVT-20250710-022:** - Track replications using current agentic tools and larger developer samples. - Measure quality-adjusted output and total review/rework time, not completion time alone.
- **EVT-20250713-024:** - Track performance dispersion across repository types, applications and private codebases. - Compare benchmark results with production merge, rollback and intervention rates.
- **EVT-20250729-020:** - Track repeated survey measures of current agent use and trust. - Compare self-reported productivity with controlled task and production-quality outcomes.
- **EVT-20250820-016:** - Track changes in included credits, overage rates and task/session definitions. - Seek customer-level data on spend expansion, retention and realized engineering output.
- **EVT-20250923-021:** - Archive and inspect the full DORA report methodology and capability model. - Track whether deployment outcomes correlate with delivery-system maturity after controlling for tool choice.
- **EVT-20251002-017:** - Track task completion, human-intervention and pull-request merge rates. - Track whether repository and CI vendors bundle agent execution into existing plans.
- **EVT-20251106-018:** - Seek task denominators, rollback rates, review time and production incidents. - Track whether the internal orchestration and evaluation layer becomes standardized or commercially sourced.
- **EVT-20260224-023:** - Track redesigned studies that accommodate task selection and concurrent agents. - Seek production telemetry linking agent usage, task mix, quality and total labor time.
- **EVT-20260406-019:** - Seek controlled comparisons across proprietary and familiar open-source repositories. - Measure end-to-end success, maintenance cost and stale-context failure rates.
