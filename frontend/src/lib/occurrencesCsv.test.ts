// SPDX-License-Identifier: EUPL-1.2
import { describe, expect, it } from 'vitest';

import { occurrencesCsv } from './occurrencesCsv';

const HEADERS = {
  code: 'Code',
  table: 'Tableau',
  row: 'Ligne',
  column: 'Colonne',
  value: 'Valeur',
  targetTable: 'Tableau attendu',
  targetColumn: 'Colonne attendue',
  side: 'Côté',
};

describe('occurrencesCsv', () => {
  it('writes one line per occurrence, with semicolons and a byte order mark', () => {
    const csv = occurrencesCsv(
      'DQ-004',
      [
        { table: 'B_05.01', row: 3, column: 'c0010', value: 'A;B "x"' },
        { table: 'B_05.01', row: 4, column: 'c0010', value: '=SUM(A1)' },
      ],
      HEADERS,
    );
    const lines = csv.slice(1).trimEnd().split('\r\n');
    expect(csv.startsWith('﻿')).toBe(true);
    expect(lines[0]).toBe(
      'Code;Tableau;Ligne;Colonne;Valeur;Tableau attendu;Colonne attendue;Côté',
    );
    expect(lines[1]).toBe('DQ-004;B_05.01;3;c0010;"A;B ""x""";;;');
    // A value that a spreadsheet would run as a formula is neutralised.
    expect(lines[2]).toBe("DQ-004;B_05.01;4;c0010;'=SUM(A1);;;");
  });
});
