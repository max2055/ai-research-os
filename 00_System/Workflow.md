# Research Object Workflow

## 1. Capture

Place source files or source notes in the appropriate `01_Inbox` subdirectory.

Do not summarize during capture if doing so would lose the original material.

## 2. Register source

Create a Source record using the Source template.

Minimum requirements:

- source identity
- publication date
- access date
- original URL or local path
- source grade
- relevant entities

## 3. Extract event

Create an Event Card only when the source contains a meaningful change, decision, result or new verifiable signal.

Separate:

- facts directly supported by the source
- inferences derived from those facts
- judgments about industry or investment impact

After an Event is created, mark Source event extraction as completed. This
processing state does not change Source `review_status`.

## 4. Link thesis

For each relevant Thesis:

- classify the Event as supporting, contradicting or contextual
- explain the relationship
- do not change confidence automatically
- propose a confidence update for human review

## 5. Update knowledge

Update stable entity profiles only with reviewed information.

Do not copy transient event narratives into entity profiles; link the Event ID instead.

## 6. Synthesize research

Working synthesis belongs in `05_Research`.

Synthesis should identify:

- what changed
- what remains unknown
- which Thesis moved
- what evidence would change the current conclusion

## 7. Publish report

Reports should use reviewed objects whenever possible and disclose unresolved conflicts.

## 8. Review

Review scopes are independent:

- Source review covers the complete Source record and provenance.
- Event review covers the claims and reasoning used in that Event.
- A reviewed Event may temporarily reference a pending Source and will retain a
  `REV003` governance warning until Source-level review is complete.
- 每次通用审核 apply 必须创建不可覆盖的 Review Decision 对象，并与目标
  `review_status` 更新在同一事务完成。
- `edit` 和 `reject` 必须记录理由；自动化不得用默认理由代替研究者决定。
- Project 过滤是派生查询；跨项目 Source 通过多个 `project_ids` 复用，不复制对象。

Weekly:

- review pending Event Cards
- examine conflicting evidence
- review proposed Thesis confidence changes
- update the research queue

Monthly:

- assess source quality
- identify framework blind spots
- archive stale objects
- revise rules only through an explicit reviewed change

Action:

- Action 必须属于至少一个 Project。
- `done` 必须记录实际 success evidence；仅完成操作而无证据不能关闭。
