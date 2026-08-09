"""Fully typed product runtime exports."""

from research_os.services.actions import (
    action_rows,
    close_action,
    prepare_action_draft,
    render_actions,
)
from research_os.services.analysis_compare import (
    compare_runs,
    render_compare_report,
)
from research_os.services.analysis_evaluator import (
    evaluate_run,
    evaluator_metrics,
    render_evaluation_packet,
    render_scorecard,
)
from research_os.services.analysis_registry import (
    ModeError,
    UnknownMode,
    find_mode,
    mode_metadata,
    mode_slug,
    mode_version,
    mode_versions,
    render_mode_check,
    render_mode_detail,
    render_mode_list,
    require_runnable,
)
from research_os.services.analysis_runner import (
    RunError,
    apply_run,
    prepare_run,
    render_run_detail,
    run_analysis,
)
from research_os.services.benchmark import run_scale_benchmark
from research_os.services.brief import (
    brief_path,
    daily_brief,
    render_daily_brief,
    write_daily_brief,
)
from research_os.services.candidate_queue import (
    enrich_candidates,
    queue_rows,
    queue_show,
    render_candidate_detail,
    render_candidate_list,
    render_enrichment,
)
from research_os.services.channels import (
    channel_rows,
    render_channel_check,
    render_channel_list,
    set_channel_enabled,
)
from research_os.services.discovery import (
    due_channels,
    render_discovery_result,
    run_discovery,
)
from research_os.services.drafts import (
    apply_event_draft,
    prepare_assertion_draft,
    prepare_entity_draft,
    prepare_event_draft,
    prepare_report_draft,
    prepare_source_draft,
    split_values,
    write_new_file,
)
from research_os.services.impact_draft import (
    apply_impact_draft,
    prepare_impact_batch,
    prepare_impact_draft,
)
from research_os.services.impact_gate import (
    gate_metrics,
    gate_metrics_from_reviews,
    gate_sample,
    render_gate_packet,
)
from research_os.services.impact_path import (
    dedup_paths,
    detect_contradictions,
    expand_impact_paths,
    path_confidence,
)
from research_os.services.impact_proposal import propose_direct_impacts
from research_os.services.indexing import (
    apply_indexes,
    index_drift,
    render_indexes,
    render_project_indexes,
)
from research_os.services.ingestion import (
    capture_existing_source,
    commit_new_source_capture,
    confirm_published_date,
    prepare_new_source_capture,
    process_source_asset,
    verify_source_assets,
)
from research_os.services.insight_proposal import propose_thesis
from research_os.services.jobs import job_rows, run_job
from research_os.services.metrics import (
    load_metrics_snapshot,
    metrics_json,
    pipeline_metrics,
    render_metrics_comparison,
    render_metrics_markdown,
    render_pipeline_metrics,
    render_universe_coverage,
    research_metrics,
    universe_coverage,
    write_metrics_snapshot,
)
from research_os.services.mode_metrics import mode_metrics, render_mode_metrics
from research_os.services.ontology import (
    ontology_jsonl,
    render_impact,
    render_scale_assessment,
    write_sqlite_export,
    write_text_export,
)
from research_os.services.pilot import pilot_status, render_pilot_status
from research_os.services.projects import (
    objects_for_project,
    prepare_project_draft,
    render_project_list,
    render_project_status,
)
from research_os.services.promote import (
    AlreadyPromoted,
    commit_promote,
    prepare_promote,
    render_promote_plan,
)
from research_os.services.release import (
    release_readiness,
    render_release_readiness,
)
from research_os.services.review_cadence import (
    advance_review_date,
    current_next_review_date,
    prepare_review_date_update,
)
from research_os.services.reviews import (
    apply_review,
    prepare_review,
    render_review_queue,
    review_queue,
)
from research_os.services.status import render_status
from research_os.services.triage import (
    dismiss_candidate,
    expire_candidates,
    purge_candidates,
    render_triage_result,
    restore_candidate,
)
from research_os.services.validation import count_by_type, validate_repository
from research_os.services.workflow import (
    EventDraftSpec,
    ReportDraftSpec,
    apply_company_update_proposal,
    load_spec,
    prepare_company_update_proposal,
    prepare_reviewable_event_draft,
    prepare_synthesized_report,
)

__all__ = [
    "ModeError",
    "RunError",
    "UnknownMode",
    "apply_event_draft",
    "advance_review_date",
    "current_next_review_date",
    "apply_company_update_proposal",
    "apply_indexes",
    "apply_impact_draft",
    "apply_review",
    "apply_run",
    "action_rows",
    "close_action",
    "compare_runs",
    "brief_path",
    "daily_brief",
    "dedup_paths",
    "detect_contradictions",
    "expand_impact_paths",
    "find_mode",
    "render_daily_brief",
    "write_daily_brief",
    "capture_existing_source",
    "commit_new_source_capture",
    "confirm_published_date",
    "count_by_type",
    "enrich_candidates",
    "evaluate_run",
    "evaluator_metrics",
    "gate_metrics",
    "gate_metrics_from_reviews",
    "gate_sample",
    "AlreadyPromoted",
    "commit_promote",
    "prepare_promote",
    "render_promote_plan",
    "index_drift",
    "job_rows",
    "load_metrics_snapshot",
    "load_spec",
    "metrics_json",
    "mode_metadata",
    "mode_metrics",
    "mode_slug",
    "mode_version",
    "mode_versions",
    "ontology_jsonl",
    "objects_for_project",
    "pipeline_metrics",
    "render_pipeline_metrics",
    "pilot_status",
    "render_pilot_status",
    "prepare_action_draft",
    "prepare_assertion_draft",
    "path_confidence",
    "prepare_review_date_update",
    "prepare_impact_batch",
    "prepare_impact_draft",
    "prepare_run",
    "propose_direct_impacts",
    "propose_thesis",
    "prepare_company_update_proposal",
    "prepare_entity_draft",
    "prepare_event_draft",
    "prepare_reviewable_event_draft",
    "prepare_new_source_capture",
    "prepare_report_draft",
    "prepare_project_draft",
    "prepare_review",
    "prepare_source_draft",
    "prepare_synthesized_report",
    "channel_rows",
    "render_channel_check",
    "render_channel_list",
    "set_channel_enabled",
    "render_compare_report",
    "render_discovery_result",
    "run_discovery",
    "due_channels",
    "render_candidate_detail",
    "render_candidate_list",
    "render_enrichment",
    "dismiss_candidate",
    "expire_candidates",
    "purge_candidates",
    "render_triage_result",
    "restore_candidate",
    "queue_rows",
    "queue_show",
    "render_indexes",
    "render_impact",
    "render_gate_packet",
    "render_metrics_comparison",
    "render_metrics_markdown",
    "render_mode_check",
    "render_mode_detail",
    "render_mode_list",
    "render_mode_metrics",
    "render_run_detail",
    "render_evaluation_packet",
    "render_scorecard",
    "render_universe_coverage",
    "render_actions",
    "render_project_indexes",
    "render_project_list",
    "render_project_status",
    "release_readiness",
    "render_release_readiness",
    "render_review_queue",
    "render_scale_assessment",
    "render_status",
    "research_metrics",
    "require_runnable",
    "review_queue",
    "run_analysis",
    "universe_coverage",
    "run_scale_benchmark",
    "run_job",
    "split_values",
    "validate_repository",
    "verify_source_assets",
    "write_new_file",
    "write_metrics_snapshot",
    "write_sqlite_export",
    "write_text_export",
    "process_source_asset",
    "EventDraftSpec",
    "ReportDraftSpec",
]
