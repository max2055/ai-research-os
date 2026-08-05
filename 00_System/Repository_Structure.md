# Repository Structure

## Directory responsibilities

| Directory | Responsibility |
|---|---|
| `00_System` | Research method, taxonomy, rules, schemas and workflow |
| `01_Inbox` | Unprocessed or partially processed source material |
| `02_Knowledge` | Stable entity profiles and accumulated knowledge |
| `03_Theses` | Active, validated, invalidated and archived hypotheses |
| `04_Evidence` | Structured Event Cards and evidence records |
| `05_Research` | Working notes and topic-level synthesis |
| `06_Reports` | Daily, weekly, topic and investment outputs |
| `07_Templates` | Canonical templates for structured objects |
| `08_Indexes` | Machine-maintained and human-readable indexes |
| `09_Automation` | Scripts, prompts, tests and automation documentation |

Structured operational objects live under:

- `05_Research/Projects/`：Project objects。
- `05_Research/Reviews/Decisions/`：immutable Review Decision objects。
- `05_Research/Reviews/Actions/`：Action objects。

## Ownership rules

- Raw material belongs in `01_Inbox` and must not be overwritten.
- Stable company, technology, product, market and person profiles belong in `02_Knowledge`.
- A claim about change over time belongs in an Event Card, not directly in a company profile.
- A testable belief belongs in `03_Theses`.
- Topic synthesis belongs in `05_Research`.
- A deliverable intended for circulation belongs in `06_Reports`.
- Templates are canonical; generated objects should follow them.

## Naming conventions

### IDs

- Source: `SRC-YYYYMMDD-NNN`
- Event: `EVT-YYYYMMDD-NNN`
- Thesis: `THS-NNN`
- Company: `COM-<slug>`
- Technology: `TEC-<slug>`
- Product: `PRD-<slug>`
- Report: `RPT-YYYYMMDD-<slug>`
- Project: `PRJ-NNN`
- Review Decision: `REV-YYYYMMDD-NNN`
- Action: `ACT-YYYYMMDD-NNN`

### Filenames

Use:

```text
<id>-<short-kebab-case-title>.md
```

Examples:

```text
EVT-20260729-001-agentforce-pricing-update.md
THS-001-agent-interface-value.md
COM-microsoft.md
```

IDs are permanent. Renaming a title must not change its ID.

## Review status

Every generated research object uses one of:

- `pending`: generated or imported, not yet reviewed
- `reviewed`: checked by the researcher
- `rejected`: unsuitable or incorrect
- `superseded`: replaced but retained for history

Only `reviewed` objects may be treated as authoritative in final reports.
