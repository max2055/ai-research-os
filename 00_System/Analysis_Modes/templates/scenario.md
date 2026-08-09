You are performing an Analysis Run for the research-OS {mode_id} mode.

# Mode contract
- Purpose: {purpose}
- Required questions:
{required_questions}
- Assumption policy: {assumption_policy}
- Evidence policy: {evidence_policy}
- Counterevidence policy: {counterevidence_policy}
- Time horizons: {time_horizons}
- Prohibited conclusions: {prohibited_conclusions}

# Frozen inputs (as-of {as_of})
{inputs}

# Output contract

Output language: write the body in Chinese (中文); the section headings below
keep their exact English names.

Produce a markdown analysis body with ALL of the following 15 sections, IN
ORDER, EACH with substantive content. The run is machine-validated for EXACT
headings: if any of the 15 headings below is missing, renamed, merged or
left empty, the run FAILS. Do not stop early and do not omit the scenario
sections — they come AFTER the nine shared sections.

## Facts used
## Inferences
## Judgments
## Contradicting evidence
## Alternative explanations
## Unknowns
## Indicators
## Mode-specific output
## Limitations
## Drivers and probabilities
## Downside scenario
## Base scenario
## Upside scenario
## Sensitivity and catalysts
## Falsification conditions

Rules:
- Facts used may cite ONLY the frozen inputs above, by permanent id.
- Separate Facts (what the inputs state) from Inferences (what follows) from
  Judgments (your assessment). Never blend them.
- Contradicting evidence and Alternative explanations must be non-empty; if the
  inputs contain no contrary signal, say so explicitly.
- Scenario probabilities are Judgments, not objective statistics — state them
  as judgments. Downside/Base/Upside each need their driver, probability,
  outcome and timeline.
- Do not reach any prohibited conclusion.
- Do not leave placeholder text.
