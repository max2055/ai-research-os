"""Explicit lifecycle transitions for authoritative research objects."""

from __future__ import annotations

from dataclasses import dataclass

from research_os.schemas.common import ReviewStatus


class InvalidTransition(ValueError):
    """Raised when a lifecycle transition violates research governance."""


REVIEW_TRANSITIONS: dict[ReviewStatus, frozenset[ReviewStatus]] = {
    ReviewStatus.PENDING: frozenset({ReviewStatus.REVIEWED, ReviewStatus.REJECTED}),
    ReviewStatus.REVIEWED: frozenset({ReviewStatus.SUPERSEDED}),
    ReviewStatus.REJECTED: frozenset({ReviewStatus.PENDING}),
    ReviewStatus.SUPERSEDED: frozenset(),
}


def transition_review(
    current: ReviewStatus | str,
    target: ReviewStatus | str,
) -> ReviewStatus:
    current_status = ReviewStatus(current)
    target_status = ReviewStatus(target)
    if current_status == target_status:
        return current_status
    if target_status not in REVIEW_TRANSITIONS[current_status]:
        raise InvalidTransition(
            f"review status cannot move from {current_status.value} "
            f"to {target_status.value}"
        )
    return target_status


@dataclass(frozen=True)
class ReportLifecycle:
    status: str
    review_status: ReviewStatus

    def publish(self) -> ReportLifecycle:
        if self.status != "draft":
            raise InvalidTransition(f"cannot publish Report from {self.status}")
        reviewed = transition_review(
            self.review_status,
            ReviewStatus.REVIEWED,
        )
        return ReportLifecycle(status="final", review_status=reviewed)

    def supersede(self) -> ReportLifecycle:
        if self.status != "final":
            raise InvalidTransition(f"cannot supersede Report from {self.status}")
        superseded = transition_review(
            self.review_status,
            ReviewStatus.SUPERSEDED,
        )
        return ReportLifecycle(status="superseded", review_status=superseded)
