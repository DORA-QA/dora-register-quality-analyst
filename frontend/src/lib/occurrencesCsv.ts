// SPDX-License-Identifier: EUPL-1.2
import { fetchOccurrences, type Occurrence } from '../api/imports';

/** Largest page the API serves (`MAX_PAGE` of the backend). */
const PAGE = 1000;

/** Every occurrence kept for one finding, read page by page. */
export async function fetchAllOccurrences(importId: string, index: number): Promise<Occurrence[]> {
  const all: Occurrence[] = [];
  for (let offset = 0; ; offset += PAGE) {
    const page = await fetchOccurrences(importId, index, offset, PAGE);
    all.push(...page.occurrences);
    if (page.occurrences.length < PAGE || all.length >= page.matching) return all;
  }
}

export interface CsvHeaders {
  code: string;
  table: string;
  row: string;
  column: string;
  value: string;
  targetTable: string;
  targetColumn: string;
  side: string;
}

function cell(value: string | number | null | undefined): string {
  const text = value === null || value === undefined ? '' : String(value);
  // A leading =, +, - or @ would be read as a formula by a spreadsheet: neutralise it.
  const safe = /^[=+\-@]/.test(text) ? `'${text}` : text;
  return /[";\n\r]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
}

/**
 * CSV for spreadsheets: semicolons (French Excel), UTF-8 with a byte order mark, so that
 * accented letters open correctly.
 */
export function occurrencesCsv(
  code: string,
  occurrences: Occurrence[],
  headers: CsvHeaders,
): string {
  const lines = [
    [
      headers.code,
      headers.table,
      headers.row,
      headers.column,
      headers.value,
      headers.targetTable,
      headers.targetColumn,
      headers.side,
    ].map(cell),
    ...occurrences.map((o) =>
      [code, o.table, o.row, o.column, o.value, o.target_table, o.target_column, o.side].map(cell),
    ),
  ];
  return '﻿' + lines.map((line) => line.join(';')).join('\r\n') + '\r\n';
}

export function downloadCsv(fileName: string, content: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
