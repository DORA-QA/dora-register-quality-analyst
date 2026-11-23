// SPDX-License-Identifier: EUPL-1.2
import { API_URL } from '../config';

/**
 * Header sent with every call (review S6): a form of another site cannot send it, and a script
 * of another site must first pass a CORS preflight, refused by the API.
 */
export const CLIENT_HEADERS = { 'X-ROI-Client': 'roi-quality-engine-web' } as const;

/** Types mirror `contracts/api_models.py` in the backend. */
export type Severity = 'BLOCKER' | 'MAJOR' | 'MINOR' | 'INFO';
export type ImportStatus = 'SUCCESS' | 'SUCCESS_WITH_WARNINGS' | 'FAILED';
export type StepStatus = 'OK' | 'WARNING' | 'FAILED' | 'SKIPPED';
export type RuleOrigin = 'OFFICIAL' | 'PO_VALIDATED' | 'TECHNICAL' | 'DATA_QUALITY';
/** REGULATORY: OFFICIAL and TECHNICAL codes; EXPERT: PO_VALIDATED and DATA_QUALITY (0.8.2). */
export type Profile = 'REGULATORY' | 'EXPERT';
export type EvaluationState = 'EVALUATED' | 'NOT_EVALUATED';

export interface Occurrence {
  table: string | null;
  row: number | null;
  column: string | null;
  value: string | null;
  /** Cross-table checks: where the value was expected. */
  target_table?: string | null;
  target_column?: string | null;
  /** Side of a contradiction between two existing values. */
  side?: 'source' | 'target' | null;
}

export interface MessageReference {
  type: 'regulatory' | 'official_guide' | 'product';
  text: string;
  verified: boolean;
}

export interface ImportMessage {
  code: string;
  severity: Severity;
  message: string;
  details: string | null;
  explanation: string | null;
  recommendation: string | null;
  expert_advice: string | null;
  reference: MessageReference | null;
  official_codes: string[];
  /** Check this finding belongs to, null when none. */
  check_id: string | null;
  /**
   * PROVISIONAL when the severity is not backed by a source read first-hand,
   * PO_VALIDATED when it is a decision of the Product Owner.
   */
  severity_status: 'CONFIRMED' | 'PROVISIONAL' | 'PO_VALIDATED';
  /** Severity under which the EBA publishes the rule applied, when it is one of its rules. */
  eba_severity?: 'warning' | 'error' | null;
  /** Origin of the rule (attribute, not a category). */
  origin?: RuleOrigin | null;
  /** Main code used by the authority, if any. */
  authority_code?: string | null;
  category?: string | null;
  /** At most 25 places where the finding was seen; row = rank of the data row (first = 1). */
  occurrences?: Occurrence[];
  occurrences_total?: number;
  /** Occurrences readable page by page with `fetchOccurrences` (0.8.3). */
  occurrences_available?: number;
  /** Position of the finding in `messages`, used to read its occurrences (0.8.3). */
  index?: number | null;
  profile?: Profile | null;
}

/** NOT_EVALUATED: the check ran but a column it reads is missing (red team RT-09). */
export type CheckStatus = 'PASSED' | 'WARNING' | 'FAILED' | 'SKIPPED' | 'NOT_EVALUATED';

export interface ImportCheck {
  id: string;
  category: string;
  name: string;
  status: CheckStatus;
  /** Codes of the findings raised by this check. */
  codes: string[];
  /** Origins of its codes, and the tables it reads and points to (Sprint 3). */
  origins?: RuleOrigin[];
  profiles?: Profile[];
  source_tables?: string[];
  target_tables?: string[];
}

export interface ImportCategory {
  key: string;
  name: string;
}

/** Provisional reading of the checks: counts and weighted score. */
export interface ImportSummary {
  checks_performed: number;
  passed: number;
  warnings: number;
  failed: number;
  rows_analysed: number;
  /** 0 to 100, null when nothing could be checked. */
  score: number | null;
  weight_earned: number;
  weight_total: number;
}

export interface ImportTable {
  code: string;
  file: string;
  rows: number;
  columns: number;
}

export interface ImportMetadata {
  channel: string | null;
  package_name: string | null;
  taxonomy_version: string | null;
  module_code: string | null;
  entity_lei: string | null;
  reporting_scope: string | null;
  country: string | null;
  reference_date: string | null;
  base_currency: string | null;
  envelope_sender_lei: string | null;
  envelope_domain: string | null;
}

/** One value of a dimension of the concentration indicators (rows of B_02.02). */
export interface ConcentrationShare {
  key: string | null;
  rows: number;
  share: number;
  providers: number | null;
  /** Label of the value in the language of the answer (since 0.8.4). */
  label?: string | null;
}

export interface ConcentrationBreakdown {
  items: ConcentrationShare[];
  not_shown: number;
}

/** Concentration indicators (Sprint 3: returned by the API, displayed from Sprint 4). */
export interface ConcentrationIndicators {
  basis: string;
  rows: number;
  providers_count: number;
  hhi: number;
  providers: {
    code: string | null;
    code_type: string | null;
    name: string | null;
    rows: number;
    share: number;
    critical_functions: number;
    critical_share: number;
  }[];
  providers_not_shown: number;
  critical_functions: number;
  critical_functions_without_provider: number;
  single_provider_critical_functions: {
    function: string;
    entity: string;
    provider: string | null;
  }[];
  single_provider_not_shown: number;
  by_headquarters_country: ConcentrationBreakdown;
  by_provision_country: ConcentrationBreakdown;
  by_service_type: ConcentrationBreakdown;
  notes: string[];
}

export interface OverviewPriority {
  /** Position of the finding in `messages`. */
  index: number | null;
  code: string;
  severity: Severity;
  finding: string;
  action: string | null;
}

/** Plain-language overview built by rules from the findings and scores (CL-37, 0.8.4). */
export interface ImportOverview {
  verdict: 'BLOCKED' | 'CORRECTIONS' | 'GOOD';
  headline: string;
  figures: string;
  tables: string | null;
  /** Verification of the LEI against the local GLEIF copy (branch gleif-local). */
  gleif?: string | null;
  priorities: OverviewPriority[];
  profiles: string | null;
  note: string;
}

export interface ImportResponse {
  import_id: string;
  /** Language of the step names and findings of this answer. */
  language: string;
  status: ImportStatus;
  source_type: string;
  tables_loaded: number;
  rows_loaded: number;
  dataset_available: boolean;
  file_name: string;
  metadata: ImportMetadata;
  rt_detected: string[];
  missing_rt: string[];
  counts: { blocker: number; major: number; minor: number; info: number };
  steps: { key: string; name: string; status: StepStatus }[];
  tables: ImportTable[];
  messages: ImportMessage[];
  summary: ImportSummary;
  categories: ImportCategory[];
  checks: ImportCheck[];
  /** Absent from older answers, null when B_02.02 is absent or empty. */
  concentration?: ConcentrationIndicators | null;
  concentration_state?: 'EVALUATED' | 'NOT_APPLICABLE' | 'INSUFFICIENT_DATA';
  /** Scores by profile, with what they are made of (0.8.2; docs/scores.md). */
  scores?: ImportScores | null;
  engine?: EngineInfo | null;
  /** Absent from answers before 0.8.4. */
  overview?: ImportOverview | null;
}

export interface ProfileScore {
  scope: 'REGULATORY' | 'QUALITY';
  /** 0 to 100, null when nothing could be computed (never shown as 0). */
  value: number | null;
  state: EvaluationState;
  weight_earned: number;
  weight_total: number;
  checks_performed: number;
  passed: number;
  warnings: number;
  failed: number;
  not_run: string[];
  not_evaluated: string[];
  not_applicable: string[];
  origins: string[];
  categories: string[];
  severities: string[];
  provisional_codes: number;
  provisional_findings: number;
}

export interface ImportScores {
  regulatory: ProfileScore;
  quality: ProfileScore;
  confidence: { value: number | null; state: EvaluationState; not_run: string[] };
  computed_at: string;
  engine_version: string;
}

export interface EngineInfo {
  version: string;
  catalog_codes: number;
  catalog_fingerprint: string;
  taxonomy_version: string | null;
}

export interface OccurrencesPage {
  import_id: string;
  index: number;
  code: string;
  /** Occurrences matching the filters, among those kept. */
  matching: number;
  offset: number;
  limit: number;
  occurrences: Occurrence[];
  occurrences_total: number;
  occurrences_available: number;
}

export interface OccurrenceFilters {
  table?: string;
  row?: number;
  column?: string;
}

/**
 * Why a call to the import API failed. It carries no text of its own, so that
 * the interface can explain it in the current language.
 */
export class ImportFailure extends Error {
  constructor(
    readonly kind: 'network' | 'http',
    /** HTTP status, for the `http` kind. */
    readonly status: number | null = null,
    /** Explanation given by the API, already written in the requested language. */
    readonly detail: string | null = null,
  ) {
    super(detail ?? kind);
  }
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { ...CLIENT_HEADERS, ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ImportFailure('network');
  }

  if (!response.ok) {
    const detail = await response
      .json()
      .then((payload: { detail?: unknown }) =>
        typeof payload.detail === 'string' ? payload.detail : null,
      )
      .catch(() => null);
    throw new ImportFailure('http', response.status, detail);
  }
  return response;
}

async function call<T = ImportResponse>(path: string, init?: RequestInit): Promise<T> {
  return (await (await send(path, init)).json()) as T;
}

/** Sends a register to the API. Findings are written in the given language. */
export function importRegister(file: File, language: string): Promise<ImportResponse> {
  const body = new FormData();
  body.append('file', file);
  return call(`/api/import?lang=${language}`, { method: 'POST', body });
}

/** Reads the last import again, in another language, without sending the file again. */
export function fetchImport(importId: string, language: string): Promise<ImportResponse> {
  return call(`/api/import/${importId}?lang=${language}`);
}

/** A page of the occurrences of one finding; the filters apply to all of them (0.8.3). */
export function fetchOccurrences(
  importId: string,
  index: number,
  offset: number,
  limit: number,
  filters: OccurrenceFilters = {},
): Promise<OccurrencesPage> {
  const query = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (filters.table) query.set('table', filters.table);
  if (filters.row !== undefined) query.set('row', String(filters.row));
  if (filters.column) query.set('column', filters.column);
  return call<OccurrencesPage>(`/api/import/${importId}/findings/${index}/occurrences?${query}`);
}

/** Forgets an analysis now: its findings, and its register if it is the one in memory. */
export async function deleteImport(importId: string): Promise<void> {
  await send(`/api/import/${importId}`, { method: 'DELETE' });
}

export interface ExportOptions {
  format: 'csv' | 'jsonl';
  language: string;
  /** Positions of the findings to export (the filters of the screen). */
  findings: number[];
  table?: string;
  row?: number | null;
  column?: string;
  /** False: the values from the register are left out. */
  values: boolean;
}

/** Address of the export: opened by the browser, streamed to the disk of this computer only. */
export function exportUrl(importId: string, options: ExportOptions): string {
  const query = new URLSearchParams({ lang: options.language, values: String(options.values) });
  query.set('findings', options.findings.join(','));
  if (options.table) query.set('table', options.table);
  if (options.row) query.set('row', String(options.row));
  if (options.column) query.set('column', options.column);
  return `${API_URL}/api/import/${encodeURIComponent(importId)}/export.${options.format}?${query}`;
}
