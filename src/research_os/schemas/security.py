"""Security entity metadata schema (v0.3).

A Security is a tradeable instrument issued by a Company. Company and
Security are deliberately separated (RCP-v03-003 review point 5) so the system
can model multi-listing, ADRs, private companies and instrument changes. A
Company references its Securities via ``security_ids`` (Company v0.3 extension);
a Security back-references its issuer via ``issuer_company_id``.

Permanent ID: ``INS-<market>-<ticker>`` (``INS`` = instrument). The
``<market>`` segment is fixed-width ``[A-Z]{2,6}`` (e.g. ``NASDAQ``=6,
``HK``=2) so the parser can disambiguate the hyphen boundary versus a ticker
that itself contains hyphens (A-006 parser ambiguity D2). Tickers may contain
``[A-Z0-9.-]``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import StringConstraints

from research_os.schemas.common import DateString, ResearchObjectSchema

# D2: market is fixed-width [A-Z]{2,6}; ticker allows [A-Z0-9.-] including
# internal hyphens. The market-width anchoring is what lets the parser split
# ``INS-NASDAQ-BRK-A`` unambiguously (market=NASDAQ, ticker=BRK-A) without
# guessing where the market ends.
SecurityId = Annotated[
    str, StringConstraints(pattern=r"^INS-[A-Z]{2,6}-[A-Z0-9][A-Z0-9.\-]*$")
]


class SecuritySchema(ResearchObjectSchema):
    """A tradeable security linked to a Company."""

    schema_version: Literal[2]
    id: SecurityId
    type: Literal["security"]

    issuer_company_id: str
    instrument_type: Literal["common_stock", "adr", "fund", "other"]
    ticker: str
    exchange: str
    currency: str
    country: str
    share_class: str = ""
    active_from: DateString
    active_to: DateString | None = None  # delisting/listing change, never delete

    # ``issuer_company_id`` format is validated as a Company ID (regex) here;
    # cross-object existence (the issuer Company actually exists) is enforced
    # in WP-103 (reference integrity), not at the schema layer.