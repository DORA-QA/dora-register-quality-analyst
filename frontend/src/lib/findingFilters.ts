// SPDX-License-Identifier: EUPL-1.2
import type { ImportMessage, ImportResponse, RuleOrigin, Severity } from '../api/imports';

/** Criteria of the findings explorer. An empty value means "no restriction". */
export interface FindingFilters {
  severity: Severity | '';
  /** Origin of the rule (CL-42): official, technical, expert check, data quality. */
  origin: RuleOrigin | '';
  /** Status of the severity (CL-42): confirmed, provisional, decided by the PO. */
  status: ImportMessage['severity_status'] | '';
  category: string;
  check: string;
  table: string;
  /** Rank of the data row (first = 1), as typed by the user. */
  row: string;
  column: string;
}

export const NO_FILTERS: FindingFilters = {
  severity: '',
  origin: '',
  status: '',
  category: '',
  check: '',
  table: '',
  row: '',
  column: '',
};

export function hasActiveFilter(filters: FindingFilters): boolean {
  return Object.values(filters).some((value) => value !== '');
}

/** Category of a finding: the one of its check, else the one it carries itself. */
export function categoryOf(message: ImportMessage, result: ImportResponse): string | null {
  const check = result.checks.find((item) => item.id === message.check_id);
  return check?.category ?? message.category ?? null;
}

/** A finding matches when every active criterion holds; place criteria must hold on one same place. */
export function matchesFilters(
  message: ImportMessage,
  result: ImportResponse,
  filters: FindingFilters,
): boolean {
  if (filters.severity && message.severity !== filters.severity) return false;
  if (filters.origin && message.origin !== filters.origin) return false;
  if (filters.status && message.severity_status !== filters.status) return false;
  if (filters.category && categoryOf(message, result) !== filters.category) return false;
  if (filters.check && message.check_id !== filters.check) return false;

  const placed = filters.table || filters.row || filters.column;
  if (!placed) return true;
  const row = filters.row.trim() === '' ? null : Number(filters.row);
  return (message.occurrences ?? []).some(
    (place) =>
      (!filters.table || place.table === filters.table) &&
      (row === null || place.row === row) &&
      (!filters.column || place.column === filters.column),
  );
}

export function filterFindings(result: ImportResponse, filters: FindingFilters): ImportMessage[] {
  return result.messages.filter((message) => matchesFilters(message, result, filters));
}

/** Distinct values offered by the table and column selectors, sorted. */
export function placeValues(messages: ImportMessage[], key: 'table' | 'column'): string[] {
  const values = new Set<string>();
  for (const message of messages) {
    for (const place of message.occurrences ?? []) {
      const value = place[key];
      if (value) values.add(value);
    }
  }
  return [...values].sort();
}
