# PRJ-002 Review Records

Weekly records live in `Weekly/`; Monthly records live in `Monthly/`.

Each completed record must contain these exact audit lines:

```text
Review status: completed
Reviewer: <human name>
Review date: YYYY-MM-DD
Metrics snapshot: <immutable snapshot path or ID>
```

The remaining content follows `07_Templates/Weekly_Review.md` or
`07_Templates/Monthly_Review.md`. A generated packet stays
`Review status: pending`; automation must not supply the Reviewer or change it to
completed.

