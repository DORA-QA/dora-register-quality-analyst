# SPDX-License-Identifier: EUPL-1.2
"""Chains the import steps: file -> validation -> tables -> RoIDataset.

This is the only place that knows every engine. The chain stops only when the
next step is technically impossible, so that one run reports as many findings
as possible. Logs carry codes and counters, never register data.

The outcome of an import holds no text: it is written in a language only when
an answer is built, so the same import can be displayed in several languages.
"""

import dataclasses
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from api.config import APP_VERSION, Settings
from api.services.results_store import ResultsStore
from contracts import data_model, identifiers, tables
from contracts.api_models import (
    CategoryModel,
    CheckModel,
    ConcentrationModel,
    ConfidenceModel,
    EngineModel,
    FindingMatchModel,
    ImportResponse,
    MessageModel,
    MetadataModel,
    OccurrenceModel,
    OccurrencesPageModel,
    ScoreModel,
    ScoresModel,
    SeverityCounts,
    StepModel,
    SummaryModel,
    TableModel,
)
from contracts.check_report import (
    catalog_fingerprint,
    category_of_code,
    check_of_code,
    evaluate_checks,
    origin_of_code,
)
from contracts.dataset import PackageMetadata
from contracts.gleif import GleifCoverage
from contracts.import_results import (
    FILE_TYPE_UNKNOWN,
    FILE_TYPE_XML,
    CsvImportResult,
    TableSummary,
)
from contracts.messages import (
    DEFAULT_LANGUAGE,
    Occurrence,
    Severity,
    ValidationMessage,
    has_blocker,
    load_catalog,
    make_message,
    render_message,
    render_text,
)
from dataset.builder import DatasetBuilder
from dataset.store import DatasetStore
from gleif.store import ParquetGleifStore
from import_engine.csv_importer import CsvImporter
from import_engine.file_type_detector import FileTypeDetector
from import_engine.onegate import check_onegate_target
from import_engine.package_validator import PackageValidator, cross_check_envelope
from import_engine.xml_validator import XmlValidator
from import_engine.xml_zip_extractor import XmlZipExtractor
from import_engine.zip_validator import ZipValidator
from indicators.concentration import Concentration, concentration
from reports.overview import build_overview
from rules.engine import RulesEngine
from rules.technical.gleif import GleifRule, coverage
from scoring import (
    ProfileScore,
    Scores,
    profile_of_code,
    profiles_of_check,
    scores,
    summarize,
)

logger = logging.getLogger("roi.import")

XSD_DIR = Path(__file__).resolve().parent.parent.parent / "reference" / "xsd"
# Keys of the steps; their names are in the language files.
STEPS = (
    "detection",
    "xml_validation",
    "extraction",
    "zip_validation",
    "package_validation",
    "csv_import",
    "dataset",
    "technical_rules",
)
Recorder = Callable[[str, list[ValidationMessage]], bool]


@dataclass
class ImportOutcome:
    """Result of an import, independent of any language."""

    import_id: str
    file_name: str
    metadata: PackageMetadata = field(default_factory=PackageMetadata)
    steps: dict[str, str] = field(default_factory=lambda: dict.fromkeys(STEPS, "SKIPPED"))
    messages: list[ValidationMessage] = field(default_factory=list)
    tables: list[TableSummary] = field(default_factory=list)
    rows_loaded: int = 0
    rt_detected: list[str] = field(default_factory=list)
    missing_rt: list[str] = field(default_factory=list)
    dataset_available: bool = False
    concentration: Concentration | None = None
    # NOT_APPLICABLE (no B_02.02 row, or no dataset), INSUFFICIENT_DATA (could not be computed).
    concentration_state: str = "NOT_APPLICABLE"
    # Codes of the rules that could not read every column they need (red team RT-09).
    blind_codes: set[str] = field(default_factory=set)
    # GLEIF verification shown in the summary (branch feature/gleif-local); None when disabled.
    gleif: GleifCoverage | None = None


class ImportService:
    def __init__(self, settings: Settings, store: DatasetStore) -> None:
        self._store = store
        self._detector = FileTypeDetector()
        self._xml_validator = XmlValidator.from_directory(XSD_DIR)
        self._extractor = XmlZipExtractor()
        self._zip_validator = ZipValidator(
            max_files=settings.max_zip_entries,
            max_uncompressed_mb=settings.max_uncompressed_mb,
        )
        self._package_validator = PackageValidator()
        self._csv_importer = CsvImporter(
            max_cell_characters=settings.max_cell_characters,
            max_columns=settings.max_columns,
            max_rows=settings.max_rows,
        )
        self._builder = DatasetBuilder()
        # GLEIF checks (branch feature/gleif-local): read the local copy, never the network.
        self._gleif = (
            ParquetGleifStore(Path(settings.gleif_dir)) if settings.gleif_enabled else None
        )
        extra = [GleifRule(self._gleif)] if self._gleif is not None else []
        self._rules = RulesEngine(extra=extra)
        # Outcomes of the last analyses (RT-13): they hold the values quoted by the findings, so
        # they follow the lifetime of the dataset (``dataset_ttl_minutes`` of inactivity).
        self._results: ResultsStore[ImportOutcome] = ResultsStore(
            ttl_seconds=settings.dataset_ttl_minutes * 60
        )

    def last_outcome(self, import_id: str) -> ImportOutcome | None:
        """Outcome of one of the last imports (two at most), as long as it has not expired."""
        return self._results.get(import_id)

    def discard(self, import_id: str) -> bool:
        """Drop one analysis on request; its dataset too when it is the one in memory."""
        found = self._results.delete(import_id)
        if self._store.get(import_id) is not None:
            self._store.purge()
        return found

    def expire(self) -> None:
        """Forget the outcomes and the dataset once their time is over."""
        self._results.expire()
        self._store.expire()

    def forget(self) -> None:
        """Drop everything kept in memory (shutdown)."""
        self._results.purge()
        self._store.purge()

    def run(self, file_path: Path, file_name: str) -> ImportOutcome:
        """Import one deposited file. ``file_path`` lives in the import workspace."""
        # The previous register is released before the new one is read: never two in memory
        # (load test of 30/10: two successive imports of 3.5 million rows went over 2 GB).
        # The findings of the previous analysis stay readable (RT-13, two at most).
        self._store.purge()
        try:
            return self._run(file_path, file_name)
        finally:
            # Identifiers and columns of the register are cached during the import only.
            identifiers.clear_caches()
            tables.clear_column_cache()

    def _run(self, file_path: Path, file_name: str) -> ImportOutcome:
        outcome = ImportOutcome(import_id=uuid.uuid4().hex, file_name=file_name)
        csv_result = CsvImportResult()

        def record(step: str, found: list[ValidationMessage]) -> bool:
            """Store the findings of a step. Returns False if the step is blocking."""
            outcome.messages.extend(found)
            if has_blocker(found):
                outcome.steps[step] = "FAILED"
            else:
                outcome.steps[step] = "WARNING" if _needs_attention(found) else "OK"
            return outcome.steps[step] != "FAILED"

        zip_path = self._prepare_zip(file_path, outcome.metadata, record)
        if zip_path is not None:
            zip_result = self._zip_validator.validate(str(zip_path))
            if record("zip_validation", zip_result.messages):
                csv_result = self._validate_and_load(zip_path, outcome, record)
        self._check_envelope_target(outcome, csv_result)

        outcome.tables = csv_result.summaries
        outcome.rows_loaded = csv_result.total_rows
        outcome.dataset_available = csv_result.total_tables > 0
        if outcome.dataset_available:
            dataset = self._builder.build(outcome.metadata, csv_result)
            self._store.put(outcome.import_id, dataset)
            outcome.steps["dataset"] = "OK"
            rules_result = self._rules.run(dataset)
            outcome.blind_codes = rules_result.blind_codes
            record("technical_rules", rules_result.messages)
            if self._gleif is not None:
                outcome.gleif = coverage(dataset, rules_result.messages, self._gleif.snapshot)
            outcome.concentration, outcome.concentration_state = _indicators(dataset)
        else:
            self._store.purge()

        self._results.put(outcome.import_id, outcome)
        logger.info(
            "import %s: status=%s source=%s tables=%d rows=%d codes=%s",
            outcome.import_id,
            _status(outcome.messages),
            outcome.metadata.source_type,
            len(outcome.tables),
            outcome.rows_loaded,
            sorted({message.code for message in outcome.messages}),
        )
        return outcome

    def _prepare_zip(
        self, file_path: Path, metadata: PackageMetadata, record: Recorder
    ) -> Path | None:
        """Return the ZIP package to analyse, extracting it from an envelope if needed."""
        if file_path.stat().st_size == 0:
            record("detection", [make_message("FILE-002")])
            return None

        detected = self._detector.detect(str(file_path)).detected_type
        metadata.source_type = detected
        if detected == FILE_TYPE_UNKNOWN:
            record("detection", [make_message("FILE-001")])
            return None
        record("detection", [])
        if detected != FILE_TYPE_XML:
            return file_path

        xml_result = self._xml_validator.validate(str(file_path))
        if not record("xml_validation", xml_result.messages):
            return None

        extracted = self._extractor.extract_zip(str(file_path))
        metadata.channel = extracted.strategy
        metadata.envelope_sender_lei = extracted.sender_lei
        metadata.envelope_domain = extracted.domain
        metadata.envelope_recipient = extracted.recipient
        if not record("extraction", extracted.messages) or extracted.zip_path is None:
            return None
        return Path(extracted.zip_path)

    def _validate_and_load(
        self, zip_path: Path, outcome: ImportOutcome, record: Recorder
    ) -> CsvImportResult:
        """Validate the package, then load its tables."""
        package = self._package_validator.validate(str(zip_path))
        envelope = outcome.metadata
        metadata = package.metadata
        metadata.source_type = envelope.source_type
        metadata.channel = envelope.channel
        metadata.envelope_sender_lei = envelope.envelope_sender_lei
        metadata.envelope_domain = envelope.envelope_domain
        metadata.envelope_recipient = envelope.envelope_recipient
        outcome.metadata = metadata
        outcome.rt_detected, outcome.missing_rt = package.rt_detected, package.missing_rt
        record(
            "package_validation",
            package.messages + cross_check_envelope(metadata.envelope_sender_lei, metadata),
        )

        # Tables are loaded even when the package has blocking findings, as long
        # as a package folder exists: the report needs the data.
        if metadata.package_name is None:
            return CsvImportResult()
        csv_result = self._csv_importer.load(str(zip_path))
        found = list(csv_result.messages)
        if csv_result.total_tables == 0:
            found.append(make_message("IMP-001"))
        record("csv_import", found)
        return csv_result

    @staticmethod
    def _check_envelope_target(outcome: ImportOutcome, csv_result: CsvImportResult) -> None:
        """ENV-005 and ENV-006, once the competent authority of the register is known.

        They belong to the extraction step; they are never blocking, so they can only turn an
        ``OK`` extraction into a ``WARNING`` one.
        """
        metadata = outcome.metadata
        found = check_onegate_target(
            metadata.envelope_recipient,
            metadata.envelope_domain,
            _competent_authority(csv_result),
        )
        if not found:
            return
        outcome.messages.extend(found)
        if outcome.steps.get("extraction") == "OK":
            outcome.steps["extraction"] = "WARNING"


def _competent_authority(csv_result: CsvImportResult) -> str | None:
    """Competent authority declared in RT.01.01.0050, None when it cannot be read."""
    table = csv_result.tables.get("B_01.01")
    if table is None or "c0050" not in table.columns:
        return None
    values = [str(v).strip() for v in table["c0050"].to_list() if v is not None and str(v).strip()]
    return values[0] if values else None


def _labelled(model: ConcentrationModel, language: str) -> ConcentrationModel:
    """Labels of countries and types of service, in the language of the answer (CL-43)."""
    for breakdown in (
        model.by_headquarters_country,
        model.by_provision_country,
        model.by_service_type,
    ):
        for item in breakdown.items:
            if item.key:
                item.label = data_model.label("member", item.key, language)
    return model


def build_response(outcome: ImportOutcome, language: str = DEFAULT_LANGUAGE) -> ImportResponse:
    """Write the outcome of an import in a language."""
    messages = outcome.messages
    counts = SeverityCounts(
        blocker=sum(m.severity is Severity.BLOCKER for m in messages),
        major=sum(m.severity is Severity.MAJOR for m in messages),
        minor=sum(m.severity is Severity.MINOR for m in messages),
        info=sum(m.severity is Severity.INFO for m in messages),
    )
    ordered = ordered_messages(outcome)
    metadata = outcome.metadata
    results = evaluate_checks(messages, outcome.steps, metadata.source_type, outcome.blind_codes)
    summary = summarize(results)
    computed = scores(results, outcome.blind_codes)
    categories = list(dict.fromkeys(r.definition.category for r in results))
    response = ImportResponse(
        import_id=outcome.import_id,
        language=language,
        status=_status(messages),
        source_type=metadata.source_type,
        tables_loaded=len(outcome.tables),
        rows_loaded=outcome.rows_loaded,
        dataset_available=outcome.dataset_available,
        file_name=outcome.file_name,
        metadata=MetadataModel(
            channel=metadata.channel,
            package_name=metadata.package_name,
            taxonomy_version=metadata.taxonomy_version,
            module_code=metadata.module_code,
            entity_lei=metadata.entity_lei,
            reporting_scope=metadata.reporting_scope,
            country=metadata.country,
            reference_date=metadata.reference_date,
            base_currency=metadata.base_currency,
            envelope_sender_lei=metadata.envelope_sender_lei,
            envelope_domain=metadata.envelope_domain,
        ),
        rt_detected=outcome.rt_detected,
        missing_rt=outcome.missing_rt,
        counts=counts,
        steps=[
            StepModel(key=key, name=render_text("steps", key, language), status=outcome.steps[key])
            for key in STEPS
        ],
        tables=[
            TableModel(
                code=summary.code,
                file=summary.file,
                rows=summary.rows,
                columns=summary.columns,
            )
            for summary in outcome.tables
        ],
        messages=[
            MessageModel.from_rendered(
                render_message(message, language),
                index=index,
                check_id=check_of_code(message.code),
                category=category_of_code(message.code),
                origin=origin_of_code(message.code),
                profile=profile_of_code(message.code),
            )
            for index, message in enumerate(ordered)
        ],
        summary=SummaryModel(
            checks_performed=summary.performed,
            passed=summary.passed,
            warnings=summary.warnings,
            failed=summary.failed,
            rows_analysed=outcome.rows_loaded,
            score=summary.score,
            weight_earned=summary.earned,
            weight_total=summary.total,
            quality_score=summary.score,
            confidence_score=summary.confidence,
        ),
        categories=[
            CategoryModel(key=key, name=render_text("categories", key, language))
            for key in categories
        ],
        checks=[
            CheckModel(
                id=r.definition.id,
                category=r.definition.category,
                name=render_text("checks", r.definition.id, language),
                status=r.status.value,
                codes=list(r.codes_found),
                origins=list(r.definition.origins),
                profiles=list(profiles_of_check(r.definition)),
                source_tables=list(r.definition.source_tables),
                target_tables=list(r.definition.target_tables),
            )
            for r in results
        ],
        concentration=(
            _labelled(
                ConcentrationModel.model_validate(dataclasses.asdict(outcome.concentration)),
                language,
            )
            if outcome.concentration
            else None
        ),
        concentration_state=outcome.concentration_state,
        scores=_scores_model(computed),
        engine=EngineModel(
            version=APP_VERSION,
            catalog_codes=len(load_catalog()),
            catalog_fingerprint=catalog_fingerprint(),
            taxonomy_version=metadata.taxonomy_version,
        ),
    )
    response.overview = build_overview(
        response.messages, counts, response.scores, language, gleif=outcome.gleif
    )
    return response


def ordered_messages(outcome: ImportOutcome) -> list[ValidationMessage]:
    """The findings in the order of the answer: the most serious first (stable sort).

    The position in this list is the ``index`` of a finding, used to read its occurrences.
    """
    order = {severity: rank for rank, severity in enumerate(Severity)}
    return sorted(outcome.messages, key=lambda m: order[m.severity])


def _matches(
    occurrence: Occurrence,
    table: str | None = None,
    row: int | None = None,
    column: str | None = None,
    target_table: str | None = None,
) -> bool:
    return (
        (table is None or table in (occurrence.table, occurrence.target_table))
        and (row is None or occurrence.row == row)
        and (column is None or column in (occurrence.column, occurrence.target_column))
        and (target_table is None or occurrence.target_table == target_table)
    )


def occurrences_page(
    outcome: ImportOutcome,
    index: int,
    offset: int,
    limit: int,
    table: str | None = None,
    row: int | None = None,
    column: str | None = None,
) -> OccurrencesPageModel | None:
    """A page of the occurrences of a finding, filters applied to all of them; None if unknown."""
    ordered = ordered_messages(outcome)
    if not 0 <= index < len(ordered):
        return None
    message = ordered[index]
    kept = [o for o in message.occurrences if _matches(o, table, row, column)]
    return OccurrencesPageModel(
        import_id=outcome.import_id,
        index=index,
        code=message.code,
        matching=len(kept),
        offset=offset,
        limit=limit,
        occurrences=[OccurrenceModel.from_occurrence(o) for o in kept[offset : offset + limit]],
        occurrences_total=max(message.occurrences_total, len(message.occurrences)),
        occurrences_available=len(message.occurrences),
    )


def matching_findings(
    outcome: ImportOutcome,
    table: str | None = None,
    row: int | None = None,
    column: str | None = None,
    target_table: str | None = None,
) -> list[FindingMatchModel]:
    """Findings with at least one occurrence matching every filter given, among all of them."""
    found = []
    for index, message in enumerate(ordered_messages(outcome)):
        count = sum(_matches(o, table, row, column, target_table) for o in message.occurrences)
        if count:
            found.append(FindingMatchModel(index=index, code=message.code, matching=count))
    return found


def _score_model(score: ProfileScore) -> ScoreModel:
    return ScoreModel(
        scope=score.scope,
        value=score.value,
        state="EVALUATED" if score.value is not None else "NOT_EVALUATED",
        weight_earned=score.earned,
        weight_total=score.total,
        checks_performed=score.performed,
        passed=score.passed,
        warnings=score.warnings,
        failed=score.failed,
        not_run=list(score.not_run),
        not_evaluated=list(score.not_evaluated),
        not_applicable=list(score.not_applicable),
        origins=list(score.origins),
        categories=list(score.categories),
        severities=list(score.severities),
        provisional_codes=score.provisional_codes,
        provisional_findings=score.provisional_findings,
    )


def _scores_model(computed: Scores) -> ScoresModel:
    return ScoresModel(
        regulatory=_score_model(computed.regulatory),
        quality=_score_model(computed.quality),
        confidence=ConfidenceModel(
            value=computed.confidence.value,
            state="EVALUATED" if computed.confidence.value is not None else "NOT_EVALUATED",
            not_run=list(computed.confidence.not_run),
        ),
        computed_at=datetime.now(UTC).isoformat(timespec="seconds"),
        engine_version=APP_VERSION,
    )


def _indicators(dataset) -> tuple[Concentration | None, str]:
    """Concentration indicators and their state; an error never stops the import.

    Only the type of the error is logged, never its text, which may quote a value.
    """
    try:
        found = concentration(dataset)
    except Exception as error:  # noqa: BLE001 - indicators are optional
        logger.warning("concentration indicators skipped: %s", type(error).__name__)
        return None, "INSUFFICIENT_DATA"
    return found, ("EVALUATED" if found else "NOT_APPLICABLE")


def _status(messages: list[ValidationMessage]) -> str:
    severities = {message.severity for message in messages}
    if Severity.BLOCKER in severities:
        return "FAILED"
    if severities & {Severity.MAJOR, Severity.MINOR}:
        return "SUCCESS_WITH_WARNINGS"
    return "SUCCESS"


def _needs_attention(found: list[ValidationMessage]) -> bool:
    return any(m.severity in (Severity.MAJOR, Severity.MINOR) for m in found)
