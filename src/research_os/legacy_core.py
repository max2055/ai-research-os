"""Compatibility facade for the former monolithic core module.

The implementation now lives in typed domain, repository and service modules.
This facade remains for one compatibility cycle so existing imports continue
to work while carrying no business logic of its own.
"""

from research_os.domain.models import Finding, ResearchObject
from research_os.domain.policies import (
    checklist_item_checked,
    headings,
    is_iso_date,
    source_processing_state,
)
from research_os.services.compatibility import (
    FrontMatterError,
    mark_sources_extracted,
    parse_front_matter,
)
from research_os.services.drafts import (
    ensure_known_ids,
    ensure_taxonomy,
    next_object_id,
    prepare_event_draft,
    prepare_report_draft,
    prepare_source_draft,
    render_event_draft,
    render_report_draft,
    render_source_draft,
    split_values,
    validate_slug,
    write_new_file,
    yaml_list,
)
from research_os.services.indexing import (
    apply_indexes,
    display,
    index_drift,
    render_indexes,
)
from research_os.services.metrics import (
    load_metrics_snapshot,
    metric_comparison_rows,
    metrics_json,
    metrics_snapshot_path,
    render_metrics_comparison,
    render_metrics_markdown,
    render_universe_coverage,
    research_metrics,
    universe_coverage,
    write_metrics_snapshot,
)
from research_os.services.ontology import (
    ontology_graph,
    ontology_jsonl,
    render_impact,
    render_scale_assessment,
    thesis_relationships,
    write_sqlite_export,
)
from research_os.services.status import render_status
from research_os.services.validation import (
    count_by_type,
    taxonomy_codes,
    validate_repository,
)

__all__ = [
    "Finding",
    "FrontMatterError",
    "ResearchObject",
    "apply_indexes",
    "checklist_item_checked",
    "count_by_type",
    "display",
    "ensure_known_ids",
    "ensure_taxonomy",
    "headings",
    "index_drift",
    "is_iso_date",
    "load_metrics_snapshot",
    "mark_sources_extracted",
    "metric_comparison_rows",
    "metrics_json",
    "metrics_snapshot_path",
    "next_object_id",
    "ontology_graph",
    "ontology_jsonl",
    "parse_front_matter",
    "prepare_event_draft",
    "prepare_report_draft",
    "prepare_source_draft",
    "render_event_draft",
    "render_impact",
    "render_indexes",
    "render_metrics_comparison",
    "render_metrics_markdown",
    "render_report_draft",
    "render_scale_assessment",
    "render_source_draft",
    "render_status",
    "render_universe_coverage",
    "research_metrics",
    "source_processing_state",
    "split_values",
    "taxonomy_codes",
    "thesis_relationships",
    "universe_coverage",
    "validate_repository",
    "validate_slug",
    "write_metrics_snapshot",
    "write_new_file",
    "write_sqlite_export",
    "yaml_list",
]
