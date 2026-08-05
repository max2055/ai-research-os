# PRJ-001 Company Review Packet

Updated: 2026-07-30

Purpose: support the human review required by RQ-07. This packet does not approve
Company objects. Review the Company body, its reviewed Event claims, pending Source
governance debt and material unknowns before recording a decision.

## Decision summary

- Companies in scope: 8
- Human decisions recorded in this packet: 8/8
- Action: `ACT-20260730-001`

| Company | Current Evidence IDs | Pending candidate Evidence | Material review focus | Human decision |
|---|---|---|---|---|
| `COM-anthropic` | `EVT-20260514-005` | — | Partner-reported adoption; private-company revenue and profitability unknown; MCP openness may distribute value away from Anthropic | approve — `REV-20260730-055` |
| `COM-microsoft` | `EVT-20260219-001`, `EVT-20260429-004` | `EVT-20260429-031` | Keep seat, usage, credits, managed-agent inventory and product revenue separate; company-wide AI ARR is not Agent revenue | approve — `REV-20260730-056` |
| `COM-openai` | `EVT-20260415-003`, `EVT-20260729-015` | — | Workspace Agents remains preview evidence; private-company economics and production adoption unknown | approve — `REV-20260730-057` |
| `COM-oracle` | `EVT-20260610-007`, `EVT-20260714-009` | — | Agent Studio is embedded/free for Fusion customers; Agent-specific use and revenue remain undisclosed | approve — `REV-20260730-058` |
| `COM-palantir` | `EVT-20260729-014` | `EVT-20260506-025` | Do not attribute company growth to AIP; implementation intensity, concentration and AIP-specific economics remain unknown | approve — `REV-20260730-059` |
| `COM-salesforce` | `EVT-20260225-002`, `EVT-20260729-012` | `EVT-20260605-030` | Vendor-defined Agentforce metrics, mixed pricing and selected customer cases require explicit attribution limits | approve — `REV-20260730-060` |
| `COM-sap` | `EVT-20260611-008`, `EVT-20260723-011` | — | Interface-migration claim is product evidence; production use, AI revenue and implementation cycle remain unknown | approve — `REV-20260730-061` |
| `COM-servicenow` | `EVT-20260722-010`, `EVT-20260729-013` | — | AI ACV and control-layer product claims do not isolate Agent economics or cross-system production adoption | approve — `REV-20260730-062` |

## Per-company checklist

For each Company:

- [ ] Company role is supported by reviewed Event facts rather than marketing
      interpretation.
- [ ] Products and distribution claims preserve product status and date.
- [ ] Business model distinguishes disclosed pricing from inferred value capture.
- [ ] Revenue and profitability do not attribute company-wide results to Agents
      without product-level disclosure.
- [ ] Competitive advantages are labeled as hypotheses or judgments.
- [ ] Contradicting Evidence, risks and unknowns are retained.
- [ ] Pending Source-level review debt is acknowledged.
- [ ] Valuation context is either sourced and date-stamped or explicitly unknown.
- [ ] Decision and notes are recorded through the generic Review workflow.

## Review command

Preview one decision:

```bash
research-os review apply \
  --targets <COM-ID> \
  --decision <approve|edit|reject> \
  --reviewer max \
  --date <YYYY-MM-DD> \
  --notes "<checked Evidence, limitations and required edits>"
```

Rerun with `--apply` only after the preview and underlying Evidence have been read.

## Completion rule

RQ-07 is complete only after all eight Company objects have explicit human
Review Decisions. A batch approval without company-specific notes does not satisfy
this packet.
