# SPDX-License-Identifier: EUPL-1.2
"""Import endpoint: deposit an XML envelope or a ZIP package."""

import logging
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from api.config import APP_VERSION, get_settings
from api.routes.gleif import current_status
from api.services.import_service import (
    ImportOutcome,
    ImportService,
    build_response,
    matching_findings,
    occurrences_page,
    ordered_messages,
)
from api.services.workspace import import_workspace
from contracts.api_models import FindingMatchModel, ImportResponse, OccurrencesPageModel
from contracts.gleif import GleifState
from contracts.messages import render_text, resolve_language, supported_languages
from reports import export
from scoring import profile_of_code

router = APIRouter(prefix="/api", tags=["import"])

CHUNK_SIZE = 1024 * 1024
MEGABYTE = 1024 * 1024
# Longest file name kept, in bytes: file systems refuse names over 255 bytes (HTTP 500 otherwise).
MAX_NAME_BYTES = 200
FALLBACK_NAME = "upload"

logger = logging.getLogger("roi.import")


def safe_file_name(name: str | None) -> str:
    """Last path component of the name sent by the client, usable as a file name."""
    file_name = Path(name or FALLBACK_NAME).name
    if "\x00" in file_name:
        return FALLBACK_NAME
    # Control and invisible formatting characters are dropped: a right-to-left override
    # would make "registre\u202ecsv.zip" look like another name on the screen (red team RT-24).
    file_name = "".join(c for c in file_name if unicodedata.category(c) not in {"Cc", "Cf"})
    if file_name in {"", ".", ".."}:
        # "..", "." or "a/../.." would name the workspace or its parent (HTTP 500).
        return FALLBACK_NAME
    if len(file_name.encode("utf-8")) > MAX_NAME_BYTES:
        suffix = Path(file_name).suffix
        return FALLBACK_NAME + (suffix if len(suffix.encode("utf-8")) <= 10 else "")
    return file_name


def _internal_error(error: Exception, language: str) -> HTTPException:
    """Unexpected failure: its type only is logged, never its text, which may quote the register."""
    logger.error("import failed: %s", type(error).__name__)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=render_text("fragments", "internal_error", language),
    )


# Review S6 (decision of the PO, 30/10/2026): a form of another site can post a file to the
# API without reading the answer. Every request that changes something must carry this header,
# which a form cannot send and which forces a CORS preflight from a script of another site.
CLIENT_HEADER = "X-ROI-Client"
# Largest page of occurrences.
MAX_PAGE = 1000


def require_client_header(
    request: Request,
    x_roi_client: Annotated[str | None, Header()] = None,
    lang: Annotated[str | None, Query()] = None,
    accept_language: Annotated[str | None, Header()] = None,
) -> None:
    if not (x_roi_client or "").strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=render_text(
                "fragments",
                "missing_client_header",
                resolve_language(lang, accept_language),
                header=CLIENT_HEADER,
            ),
        )


ClientHeader = Depends(require_client_header)


LanguageQuery = Annotated[
    str | None,
    Query(description="Language of the texts, for example 'en' or 'fr'."),
]
AcceptLanguage = Annotated[str | None, Header()]


def _service(request: Request) -> ImportService:
    return request.app.state.import_service


@router.get("/languages", summary="Languages available for the texts")
def get_languages() -> list[str]:
    """Return the supported language codes, the default one first."""
    return list(supported_languages())


@router.post(
    "/import",
    summary="Import a register (XML envelope or ZIP package)",
    dependencies=[ClientHeader],
)
def import_register(
    request: Request,
    file: UploadFile,
    lang: LanguageQuery = None,
    accept_language: AcceptLanguage = None,
) -> ImportResponse:
    """Validate the deposited file, load its tables and build the dataset.

    The file is written to a temporary folder that is deleted before the answer
    is returned. A file with findings is answered with HTTP 200 and the status
    ``FAILED`` or ``SUCCESS_WITH_WARNINGS``: findings are a result, not an error.

    The language is taken from ``lang``, else from the ``Accept-Language``
    header, else it is English.
    """
    settings = get_settings()
    language = resolve_language(lang, accept_language)
    if current_status(request).state is GleifState.UPDATING:
        # The GLEIF copy is being updated (branch feature/gleif-local): try again in a moment.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=render_text("fragments", "gleif_updating", language),
            headers={"Retry-After": "10"},
        )
    limit = settings.max_upload_mb * MEGABYTE
    # Only the last path component is kept: the name comes from the client.
    file_name = safe_file_name(file.filename)

    with import_workspace(settings.temp_dir) as workspace:
        target = workspace / file_name
        written = 0
        with target.open("wb") as handle:
            while chunk := file.file.read(CHUNK_SIZE):
                written += len(chunk)
                if written > limit:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=render_text(
                            "fragments", "file_too_large", language, limit=settings.max_upload_mb
                        ),
                    )
                handle.write(chunk)
        try:
            outcome = _service(request).run(target, file_name)
            return build_response(outcome, language)
        except Exception as error:  # noqa: BLE001 - never let a traceback quote the register
            raise _internal_error(error, language) from None


@router.get("/import/{import_id}", summary="Result of one of the last imports")
def get_import(
    request: Request,
    import_id: str,
    lang: LanguageQuery = None,
    accept_language: AcceptLanguage = None,
) -> ImportResponse:
    """Return the result of one of the last two imports, in the language requested.

    Used to display the same import in another language without importing the
    file again (red team RT-13: two tabs no longer erase each other).
    """
    language = resolve_language(lang, accept_language)
    outcome = _service(request).last_outcome(import_id)
    if outcome is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=render_text("fragments", "unknown_import", language),
        )
    try:
        return build_response(outcome, language)
    except Exception as error:  # noqa: BLE001 - never let a traceback quote the register
        raise _internal_error(error, language) from None


def _outcome(request: Request, import_id: str, language: str) -> ImportOutcome:
    outcome = _service(request).last_outcome(import_id)
    if outcome is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=render_text("fragments", "unknown_import", language),
        )
    return outcome


@router.get(
    "/import/{import_id}/findings/{index}/occurrences",
    summary="Occurrences of one finding, page by page",
)
def get_occurrences(
    request: Request,
    import_id: str,
    index: int,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = 100,
    table: Annotated[str | None, Query()] = None,
    row: Annotated[int | None, Query(ge=1)] = None,
    column: Annotated[str | None, Query()] = None,
    lang: LanguageQuery = None,
    accept_language: AcceptLanguage = None,
) -> OccurrencesPageModel:
    """Every occurrence of a finding, beyond the 25 of the answer (Sprint 4, lot 3).

    ``index`` is the position of the finding in ``messages`` (its ``index`` field). The
    filters apply to every occurrence kept, before the page is cut.
    """
    language = resolve_language(lang, accept_language)
    outcome = _outcome(request, import_id, language)
    page = occurrences_page(outcome, index, offset, limit, table=table, row=row, column=column)
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=render_text("fragments", "unknown_finding", language),
        )
    return page


@router.get(
    "/import/{import_id}/findings",
    summary="Findings having an occurrence at a given place",
)
def search_findings(
    request: Request,
    import_id: str,
    table: Annotated[str | None, Query()] = None,
    row: Annotated[int | None, Query(ge=1)] = None,
    column: Annotated[str | None, Query()] = None,
    target_table: Annotated[str | None, Query()] = None,
    lang: LanguageQuery = None,
    accept_language: AcceptLanguage = None,
) -> list[FindingMatchModel]:
    """The findings with at least one occurrence matching every filter given, among all of them.

    Brief of the Sprint 4, §7: the filters on table, row and column go through every
    occurrence, not only the 25 of the answer.
    """
    language = resolve_language(lang, accept_language)
    outcome = _outcome(request, import_id, language)
    return matching_findings(
        outcome, table=table, row=row, column=column, target_table=target_table
    )


@router.delete(
    "/import/{import_id}",
    summary="Forget an analysis now",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[ClientHeader],
)
def delete_import(request: Request, import_id: str) -> Response:
    """Drop the findings of an analysis, and its register if it is the one in memory.

    Answers 204 whether or not the analysis was still known: the result is the same.
    """
    _service(request).discard(import_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _export_indices(findings: str | None, language: str) -> set[int] | None:
    if not findings:
        return None
    try:
        return {int(part) for part in findings.split(",") if part.strip()}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=render_text("fragments", "unknown_finding", language),
        ) from None


@router.get(
    "/import/{import_id}/export.{extension}",
    summary="Export of the findings, as CSV or JSON Lines",
    response_class=StreamingResponse,
)
def export_findings(
    request: Request,
    import_id: str,
    extension: Literal["csv", "jsonl"],
    findings: Annotated[
        str | None, Query(description="Indices of the findings, comma separated")
    ] = None,
    table: Annotated[str | None, Query()] = None,
    row: Annotated[int | None, Query(ge=1)] = None,
    column: Annotated[str | None, Query()] = None,
    values: bool = True,
    lang: LanguageQuery = None,
    accept_language: AcceptLanguage = None,
) -> StreamingResponse:
    """Every occurrence of the findings shown, one line each (Sprint 4, lot 3, §15 and §16).

    Generated on demand, as a stream: nothing is written to disk nor kept after sending.
    ``values=false`` leaves out the values from the register. The file name never carries
    the name of the file analysed.
    """
    language = resolve_language(lang, accept_language)
    outcome = _outcome(request, import_id, language)
    lines = export.rows(
        ordered_messages(outcome),
        import_id=outcome.import_id,
        engine_version=APP_VERSION,
        language=language,
        indices=_export_indices(findings, language),
        table=table,
        row=row,
        column=column,
        include_values=values,
        profile_of=profile_of_code,
    )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    file_name = f"roi-findings-{outcome.import_id}-{stamp}.{extension}"
    stream, media = (
        (export.csv_stream(lines), "text/csv; charset=utf-8")
        if extension == "csv"
        else (export.jsonl_stream(lines), "application/x-ndjson; charset=utf-8")
    )
    return StreamingResponse(
        stream,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Cache-Control": "no-store",
        },
    )
