// SPDX-License-Identifier: EUPL-1.2
import { describe, expect, it } from 'vitest';

import type { ImportMessage, ImportResponse } from '../api/imports';
import { filterFindings, NO_FILTERS, placeValues } from './findingFilters';

function message(over: Partial<ImportMessage>): ImportMessage {
  return {
    code: 'X',
    severity: 'MAJOR',
    message: 'm',
    details: null,
    explanation: null,
    recommendation: null,
    expert_advice: null,
    reference: null,
    official_codes: [],
    check_id: null,
    severity_status: 'CONFIRMED',
    ...over,
  };
}

const RESULT = {
  categories: [
    { key: 'zip', name: 'ZIP' },
    { key: 'dat', name: 'Data' },
  ],
  checks: [
    { id: 'c1', category: 'zip', name: 'One', status: 'FAILED', codes: [] },
    { id: 'c2', category: 'dat', name: 'Two', status: 'FAILED', codes: [] },
  ],
  messages: [
    message({ code: 'A', severity: 'BLOCKER', check_id: 'c1' }),
    message({
      code: 'B',
      check_id: 'c2',
      occurrences: [
        { table: 'B_01.01', row: 2, column: 'c0010', value: 'x' },
        { table: 'B_02.01', row: 5, column: 'c0020', value: null },
      ],
    }),
  ],
} as unknown as ImportResponse;

const codes = (filters: Partial<typeof NO_FILTERS>) =>
  filterFindings(RESULT, { ...NO_FILTERS, ...filters }).map((item) => item.code);

describe('filterFindings', () => {
  it('keeps everything without filter', () => {
    expect(codes({})).toEqual(['A', 'B']);
  });

  it('filters by severity, category and check', () => {
    expect(codes({ severity: 'BLOCKER' })).toEqual(['A']);
    expect(codes({ category: 'dat' })).toEqual(['B']);
    expect(codes({ check: 'c1' })).toEqual(['A']);
  });

  it('requires table, row and column to hold on one same place', () => {
    expect(codes({ table: 'B_01.01', row: '2' })).toEqual(['B']);
    expect(codes({ table: 'B_01.01', row: '5' })).toEqual([]);
    expect(codes({ column: 'c0020' })).toEqual(['B']);
  });

  it('finds a finding through any of its occurrences, not only the first (CL-27)', () => {
    const many = {
      ...RESULT,
      messages: [
        message({
          code: 'ONE',
          check_id: 'c2',
          occurrences: [{ table: 'B_05.01', row: 3, column: 'c0010', value: 'v' }],
        }),
        message({
          code: 'MANY',
          check_id: 'c2',
          occurrences: [
            { table: 'B_05.01', row: 12, column: 'c0010', value: 'a' },
            { table: 'B_05.01', row: 28, column: 'c0010', value: 'b' },
            { table: 'B_05.01', row: 44, column: 'c0020', value: 'c' },
          ],
        }),
      ],
    } as unknown as ImportResponse;
    const found = (filters: Partial<typeof NO_FILTERS>) =>
      filterFindings(many, { ...NO_FILTERS, ...filters }).map((item) => item.code);

    expect(found({ row: '3' })).toEqual(['ONE']);
    expect(found({ row: '28' })).toEqual(['MANY']);
    expect(found({ column: 'c0020' })).toEqual(['MANY']);
    expect(found({ row: '44', column: 'c0020' })).toEqual(['MANY']);
    expect(found({ table: 'B_05.01', row: '28', column: 'c0010' })).toEqual(['MANY']);
    // Row and column must hold on one same occurrence.
    expect(found({ row: '28', column: 'c0020' })).toEqual([]);
    // A row typed with spaces is still a row.
    expect(found({ row: ' 12 ' })).toEqual(['MANY']);
  });

  it('lists the distinct places', () => {
    expect(placeValues(RESULT.messages, 'table')).toEqual(['B_01.01', 'B_02.01']);
  });
});
