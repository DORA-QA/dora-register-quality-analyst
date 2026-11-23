# SPDX-License-Identifier: EUPL-1.2
"""Models returned by the REST API for an import."""

from typing import Literal

from pydantic import BaseModel

from contracts.messages import Occurrence, RenderedMessage

ImportStatus = Literal["SUCCESS", "SUCCESS_WITH_WARNINGS", "FAILED"]


class ReferenceModel(BaseModel):
    type: str
    text: str
    verified: bool


class OccurrenceModel(BaseModel):
    table: str | None = None
    row: int | None = None
    column: str | None = None
    value: str | None = None
    # Cross-table checks: table and column where the value was expected, side of a conflict.
    target_table: str | None = None
    target_column: str | None = None
    side: Literal["source", "target"] | None = None

    @classmethod
    def from_occurrence(cls, occurrence: Occurrence) -> "OccurrenceModel":
        side = occurrence.side if occurrence.side in ("source", "target") else None
        return cls(
            table=occurrence.table,
            row=occurrence.row,
            column=occurrence.column,
            value=occurrence.value,
            target_table=occurrence.target_table,
            target_column=occurrence.target_column,
            side=side,
        )


class MessageModel(BaseModel):
    code: str
    severity: str
    message: str
    details: str | None = None
    explanation: str | None = None
    recommendation: str | None = None
    expert_advice: str | None = None
    reference: ReferenceModel | None = None
    official_codes: list[str] = []
    check_id: str | None = None
    # CONFIRMED, PROVISIONAL or PO_VALIDATED.
    severity_status: str = "CONFIRMED"
    # OFFICIAL, PO_VALIDATED, TECHNICAL or DATA_QUALITY (CL-30): an attribute, not a category.
    origin: str | None = None
    # REGULATORY (OFFICIAL, TECHNICAL) or EXPERT (PO_VALIDATED, DATA_QUALITY), since 0.8.2.
    profile: str | None = None
    authority_code: str | None = None
    category: str | None = None
    occurrences: list[OccurrenceModel] = []
    occurrences_total: int = 0
    # Since 0.8.3: occurrences readable page by page (the first 25 are in ``occurrences``),
    # and the position of the finding in ``messages``, used to read them.
    occurrences_available: int = 0
    index: int | None = None
    # Since 0.8.4 (#179): severity published by the EBA for the rule applied, if any.
    eba_severity: str | None = None

    @classmethod
    def from_rendered(
        cls,
        message: RenderedMessage,
        index: int | None = None,
        check_id: str | None = None,
        category: str | None = None,
        origin: str | None = None,
        profile: str | None = None,
    ) -> "MessageModel":
        return cls(
            code=message.code,
            severity=message.severity.value,
            message=message.message,
            details=message.details,
            explanation=message.explanation,
            recommendation=message.recommendation,
            expert_advice=message.expert_advice,
            reference=ReferenceModel(
                type=message.reference.type.value,
                text=message.reference.text,
                verified=message.reference.verified,
            )
            if message.reference
            else None,
            official_codes=list(message.official_codes),
            check_id=check_id,
            severity_status=message.severity_status,
            authority_code=message.authority_code,
            eba_severity=message.eba_severity,
            category=category,
            origin=origin,
            profile=profile,
            occurrences=[OccurrenceModel.from_occurrence(o) for o in message.occurrences],
            occurrences_total=message.occurrences_total,
            occurrences_available=message.occurrences_available,
            index=index,
        )


class OccurrencesPageModel(BaseModel):
    """A page of the occurrences of one finding (Sprint 4, lot 3)."""

    import_id: str
    index: int
    code: str
    # Occurrences matching the filters, among those kept in memory.
    matching: int
    offset: int
    limit: int
    occurrences: list[OccurrenceModel]
    # Real number of occurrences of the finding, and how many are kept in memory.
    occurrences_total: int
    occurrences_available: int


class FindingMatchModel(BaseModel):
    """A finding with at least one occurrence matching a search, and how many match."""

    index: int
    code: str
    matching: int


class StepModel(BaseModel):
    key: str
    name: str
    status: Literal["OK", "WARNING", "FAILED", "SKIPPED"]


class TableModel(BaseModel):
    code: str
    file: str
    rows: int
    columns: int


class MetadataModel(BaseModel):
    channel: str | None = None
    package_name: str | None = None
    taxonomy_version: str | None = None
    module_code: str | None = None
    entity_lei: str | None = None
    reporting_scope: str | None = None
    country: str | None = None
    reference_date: str | None = None
    base_currency: str | None = None
    envelope_sender_lei: str | None = None
    envelope_domain: str | None = None


class SeverityCounts(BaseModel):
    blocker: int = 0
    major: int = 0
    minor: int = 0
    info: int = 0


class CheckModel(BaseModel):
    id: str
    category: str
    name: str
    status: Literal["PASSED", "WARNING", "FAILED", "SKIPPED", "NOT_EVALUATED"]
    codes: list[str] = []
    # Origins of the codes of the check (CL-30), and the tables they read and point to.
    origins: list[str] = []
    # Profiles of its codes (REGULATORY, EXPERT); a check may hold both (since 0.8.2).
    profiles: list[str] = []
    source_tables: list[str] = []
    target_tables: list[str] = []


class CategoryModel(BaseModel):
    key: str
    name: str


class SummaryModel(BaseModel):
    """Provisional reading of the checks: counts and weighted score."""

    checks_performed: int
    passed: int
    warnings: int
    failed: int
    rows_analysed: int
    # 0 to 100, None when nothing could be checked.
    score: int | None
    # Weight earned and total weight, so the screen can show the formula.
    weight_earned: float
    weight_total: int
    # Quality score (the former ``score``), same scale; confidence is 100, or 0 after a blocker.
    quality_score: int | None = None
    confidence_score: int | None = None


EvaluationState = Literal["EVALUATED", "NOT_EVALUATED"]


class ScoreModel(BaseModel):
    """One score and what it is made of (Sprint 4, brief §11; formula in docs/scores.md)."""

    # REGULATORY (OFFICIAL and TECHNICAL codes) or QUALITY (every code).
    scope: str
    # 0 to 100; None when no check concerns the file (never shown as 0).
    value: int | None
    state: EvaluationState
    weight_earned: float
    weight_total: int
    checks_performed: int
    passed: int
    warnings: int
    failed: int
    # Checks concerning the file that earned nothing: did not run, or a column was missing.
    not_run: list[str] = []
    not_evaluated: list[str] = []
    # Checks that do not concern the file (out of the total).
    not_applicable: list[str] = []
    origins: list[str] = []
    categories: list[str] = []
    severities: list[str] = []
    # Provisional rules are counted at their severity; how many there are, and their findings.
    provisional_codes: int = 0
    provisional_findings: int = 0


class ConfidenceModel(BaseModel):
    """100 without blocker, 0 after one, None when a check concerning the file did not run."""

    value: int | None
    state: EvaluationState
    not_run: list[str] = []


class ScoresModel(BaseModel):
    """Internal quality indicators, without regulatory value (Sprint 4, lot 2)."""

    regulatory: ScoreModel
    quality: ScoreModel
    confidence: ConfidenceModel
    # When and by which engine the scores were computed (ISO 8601, UTC).
    computed_at: str
    engine_version: str


class EngineModel(BaseModel):
    """Versions behind an analysis: engine, catalogue of checks and taxonomy."""

    version: str
    catalog_codes: int
    # First 12 characters of the SHA-256 of the registry and the catalogue of messages.
    catalog_fingerprint: str
    taxonomy_version: str | None = None


class ShareModel(BaseModel):
    """One value of a dimension: rows of B_02.02 and their share (0 to 1)."""

    key: str | None
    rows: int
    share: float
    # Distinct direct providers behind the value (country of the head office only).
    providers: int | None = None
    # Since 0.8.4 (CL-43): label of the value in the language of the answer (ITS or EBA).
    label: str | None = None


class BreakdownModel(BaseModel):
    items: list[ShareModel]
    # Values beyond the 50 largest, not listed.
    not_shown: int = 0


class ProviderShareModel(BaseModel):
    code: str | None
    code_type: str | None
    name: str | None
    rows: int
    share: float
    # Critical or important functions supported, and their share of all those supported.
    critical_functions: int
    critical_share: float


class SingleProviderFunctionModel(BaseModel):
    function: str
    entity: str
    provider: str | None


class ConcentrationModel(BaseModel):
    """Concentration indicators (Sprint 3, API only; formulas in docs/concentration.md)."""

    basis: str
    rows: int
    providers_count: int
    # Herfindahl-Hirschman index on the shares of rows, 0 to 10 000.
    hhi: float
    providers: list[ProviderShareModel]
    providers_not_shown: int
    critical_functions: int
    critical_functions_without_provider: int
    single_provider_critical_functions: list[SingleProviderFunctionModel]
    single_provider_not_shown: int
    by_headquarters_country: BreakdownModel
    by_provision_country: BreakdownModel
    by_service_type: BreakdownModel
    notes: list[str] = []


class OverviewPriorityModel(BaseModel):
    """One of the priorities of the overview: a finding and what to do."""

    # Position of the finding in ``messages``.
    index: int | None = None
    code: str
    severity: str
    finding: str
    action: str | None = None


class OverviewModel(BaseModel):
    """Plain-language overview built by rules from the findings and scores (CL-37, 0.8.4)."""

    # BLOCKED (at least one BLOCKER), CORRECTIONS (at least one MAJOR) or GOOD.
    verdict: Literal["BLOCKED", "CORRECTIONS", "GOOD"]
    headline: str
    figures: str
    # Tables most concerned, None when no finding is located in a table.
    tables: str | None = None
    # Verification of the LEI against the GLEIF copy (branch gleif-local), None when disabled.
    gleif: str | None = None
    priorities: list[OverviewPriorityModel] = []
    # Split between official rules and expert advice, None without findings.
    profiles: str | None = None
    note: str


class ImportResponse(BaseModel):
    """Result of ``POST /api/import``."""

    import_id: str
    # Language of the texts of this answer (step names and findings).
    language: str
    status: ImportStatus
    source_type: str
    tables_loaded: int
    rows_loaded: int
    # True when the dataset is kept in memory for the analysis.
    dataset_available: bool
    file_name: str
    metadata: MetadataModel
    rt_detected: list[str]
    missing_rt: list[str]
    counts: SeverityCounts
    steps: list[StepModel]
    tables: list[TableModel]
    messages: list[MessageModel]
    summary: SummaryModel
    categories: list[CategoryModel]
    checks: list[CheckModel]
    # Concentration indicators, None when B_02.02 is absent or empty (Sprint 3, no display).
    concentration: ConcentrationModel | None = None
    # Why ``concentration`` is None (Sprint 4, §13): NOT_APPLICABLE without B_02.02 rows,
    # INSUFFICIENT_DATA when it could not be computed. EVALUATED otherwise.
    concentration_state: Literal["EVALUATED", "NOT_APPLICABLE", "INSUFFICIENT_DATA"] = (
        "NOT_APPLICABLE"
    )
    # Since 0.8.2: scores by profile and the versions behind them. ``summary`` is kept as in 0.8.0.
    scores: ScoresModel | None = None
    engine: EngineModel | None = None
    # Since 0.8.4 (CL-37): plain-language overview, in the language of the answer.
    overview: OverviewModel | None = None
