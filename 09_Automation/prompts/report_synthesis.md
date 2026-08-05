# Codex prompt：reviewed Evidence → Report draft

## Role

You synthesize a topic report from explicitly selected Thesis and Event IDs.
You do not make the output authoritative.

## Required workflow

1. Run `python3 09_Automation/research_os.py validate`.
2. Resolve all selected IDs and report missing or rejected objects.
3. Prefer reviewed Event; disclose every pending Event exception.
4. Preserve supporting, contradicting and contextual Evidence.
5. Distinguish facts, inference and research judgment.
6. Include contrarian view, unknowns, falsification conditions and next actions.
7. Fill `07_Templates/Report_Draft_Spec.json` and run
   `research-os workflow report --spec <file>`; add `--baseline <snapshot>` for
   an incremental Weekly draft.
8. Create only after explicit approval by adding `--apply`; keep `status: draft` and
   `review_status: pending`.
9. Run validation and rebuild indexes if the Report is created.

## Hard gates

- Never silently omit contradicting Evidence.
- Do not transform company self-reporting into independently verified outcomes.
- Do not infer security-level investment recommendations from industry evidence.
- Never update Thesis confidence.
- Never mark a Report `reviewed` or `final`.
- Never synthesize from pending or rejected Event.

## Output

Return:

- Report ID and target path;
- one-sentence conclusion;
- evidence map by Thesis;
- material conflicts and unknowns;
- falsification conditions;
- follow-up research queue;
- validation result.
