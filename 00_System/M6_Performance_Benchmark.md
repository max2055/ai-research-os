# M6 Performance Benchmark

Status: passed

Run date: 2026-07-29  
Target: AI Research OS v0.2 M6-06  
Command: `research-os benchmark --sources 1000 --events 500 --max-seconds 10`

## Result

Sources: 1000

Events: 500

| Measure | Result |
|---|---:|
| Formal objects | 1,501 |
| Validation errors | 0 |
| Validation | 1.8558 s |
| Global index render | 0.0042 s |
| Project index render | 0.0043 s |
| Total query time | 1.8643 s |
| Maximum accepted | 10.0 s |

Decision: pass

## Method

- `research-os benchmark` creates a temporary Markdown repository; it does not write
  synthetic objects into the research Vault.
- The generated set contains one Project, 1,000 Source objects and 500 Event objects.
- Measured query time includes full formal validation plus global and Project index
  rendering. Temporary fixture generation is outside the query measurement.
- The benchmark is deterministic, has a smaller automated regression test and can be
  rerun on another machine.

## Interpretation

The current Markdown-first architecture remains usable at the roadmap trigger scale.
This result does not prove that every future relationship query or full-text search
will remain fast. It means the M6 baseline does not justify adding a permanent
SQLite or graph database.

