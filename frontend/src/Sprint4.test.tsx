// SPDX-License-Identifier: EUPL-1.2
/**
 * Interface tests asked by the Sprint 4 brief (§31.1) that App.test.tsx did not cover yet
 * (CL-48): combined filters, states of the concentration indicators, French for the panels of
 * the sprint, complete export with the filters of the screen, keyboard use of the new controls.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { ImportMessage, ImportResponse } from './api/imports';
import { deposit, FAILED_IMPORT, json, mockApi, renderApp } from './test/app';

const BASE = FAILED_IMPORT.messages[0];

function finding(
  index: number,
  code: string,
  message: string,
  extra: Partial<ImportMessage>,
): ImportMessage {
  return { ...BASE, index, code, message, ...extra };
}

/** Three findings: two official on different tables, one expert advice on the same row as one. */
const THREE: ImportResponse = {
  ...FAILED_IMPORT,
  counts: { blocker: 1, major: 1, minor: 0, info: 1 },
  messages: [
    finding(0, 'PKG-010', 'Official blocker on B_01.01', {
      severity: 'BLOCKER',
      profile: 'REGULATORY',
      origin: 'OFFICIAL',
      occurrences: [{ table: 'B_01.01', row: 3, column: 'c0010', value: 'a' }],
      occurrences_total: 1,
    }),
    finding(1, 'DAT-022', 'Official major on B_05.01', {
      severity: 'MAJOR',
      profile: 'REGULATORY',
      origin: 'OFFICIAL',
      occurrences: [{ table: 'B_05.01', row: 7, column: 'c0050', value: 'b' }],
      occurrences_total: 1,
    }),
    finding(2, 'DQ-004', 'Expert advice on B_05.01', {
      severity: 'INFO',
      profile: 'EXPERT',
      origin: 'DATA_QUALITY',
      severity_status: 'PO_VALIDATED',
      occurrences: [{ table: 'B_05.01', row: 7, column: 'c0010', value: 'c' }],
      occurrences_total: 1,
    }),
  ],
};

const SCORE = {
  weight_earned: 8.5,
  weight_total: 13,
  checks_performed: 5,
  passed: 3,
  warnings: 1,
  failed: 1,
  not_evaluated: [],
  not_applicable: [],
  origins: [],
  categories: [],
  severities: [],
  provisional_codes: 0,
  provisional_findings: 0,
};

async function choose(label: string, option: string) {
  await userEvent.click(screen.getByLabelText(label));
  await userEvent.click(await screen.findByRole('option', { name: option }));
}

describe('Combined filters (brief §7, §31.1)', () => {
  it('combines the view, the table, the row and the severity, then resets them', async () => {
    mockApi(async () => json(THREE));
    renderApp();
    await deposit();
    expect(await screen.findByText('3 of 3 findings shown')).toBeInTheDocument();

    await choose('Table', 'B_05.01');
    expect(screen.getByText('2 of 3 findings shown')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Regulatory view' }));
    expect(screen.getByText(/^1 of 3 findings shown/)).toBeInTheDocument();
    expect(screen.getByText('Official major on B_05.01')).toBeInTheDocument();
    expect(screen.queryByText('Expert advice on B_05.01')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'All findings' }));
    await userEvent.type(screen.getByLabelText('Row'), '7');
    await choose('Severity', 'INFO');
    expect(screen.getByText('1 of 3 findings shown')).toBeInTheDocument();
    expect(screen.getByText('Expert advice on B_05.01')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(screen.getByText('3 of 3 findings shown')).toBeInTheDocument();
  });

  it('exports in CSV only the findings left by the filters, with the place filters', async () => {
    mockApi(async () => json(THREE));
    const clicked: string[] = [];
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clicked.push(this.href);
    });
    renderApp();
    await deposit();
    await screen.findByText('3 of 3 findings shown');

    await choose('Table', 'B_05.01');
    await userEvent.click(screen.getByRole('button', { name: 'Export the findings' }));
    const dialog = screen.getByRole('dialog', { name: 'Export the findings shown' });
    expect(within(dialog).getByText(/^2 finding\(s\)/)).toBeVisible();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Download' }));

    const url = new URL(clicked[0]);
    expect(url.pathname).toBe(`/api/import/${THREE.import_id}/export.csv`);
    expect(url.searchParams.get('findings')).toBe('1,2');
    expect(url.searchParams.get('table')).toBe('B_05.01');
    expect(url.searchParams.get('values')).not.toBe('false');
    click.mockRestore();
  });
});

describe('Concentration indicators when they cannot be calculated (brief §13)', () => {
  it.each([
    ['INSUFFICIENT_DATA', /data of B_02\.02 is not sufficient/],
    ['NOT_APPLICABLE', /no row in B_02\.02/],
  ] as const)('says %s in words and shows no figure', async (state, text) => {
    mockApi(async () =>
      json({ ...FAILED_IMPORT, concentration_state: state, concentration: null }),
    );
    renderApp();
    await deposit();

    await userEvent.click(await screen.findByRole('button', { name: /Concentration indicators/ }));
    expect(screen.getByText(text)).toBeVisible();
    expect(screen.queryByText(/Herfindahl/)).not.toBeInTheDocument();
    expect(screen.queryByText(/ 0 %/)).not.toBeInTheDocument();
  });
});

describe('The panels of the sprint in French (brief §31.1)', () => {
  it('shows the scores, the warning, the views, the concentration and the export in French', async () => {
    mockApi(async () =>
      json({
        ...THREE,
        language: 'fr',
        concentration_state: 'NOT_APPLICABLE',
        concentration: null,
        scores: {
          regulatory: { ...SCORE, scope: 'REGULATORY', value: 88, state: 'EVALUATED', not_run: [] },
          quality: {
            ...SCORE,
            scope: 'QUALITY',
            value: null,
            state: 'NOT_EVALUATED',
            not_run: ['ENV'],
          },
          confidence: { value: 0, state: 'EVALUATED', not_run: [] },
          computed_at: '2026-11-07T18:00:00+00:00',
          engine_version: '0.8.7',
        },
      }),
    );
    renderApp();
    await userEvent.click(screen.getByRole('button', { name: 'Français' }));
    await deposit('Fichier du registre');

    const result = await screen.findByRole('region', { name: "Résultat de l'import" });
    expect(within(result).getByText(/Score réglementaire\s?: 88\/100/)).toBeVisible();
    expect(within(result).getByText(/Score qualité\s?: non évalué/)).toBeVisible();
    expect(within(result).getByText(/sans valeur réglementaire/)).toBeVisible();
    expect(within(result).getByRole('button', { name: 'Vue réglementaire' })).toBeVisible();
    expect(within(result).getByRole('button', { name: 'Vue experte' })).toBeVisible();

    await userEvent.click(
      within(result).getByRole('button', { name: /Indicateurs de concentration/ }),
    );
    expect(within(result).getByText(/Sans objet/)).toBeVisible();

    await userEvent.click(within(result).getByRole('button', { name: 'Exporter les constats' }));
    const dialog = screen.getByRole('dialog', { name: 'Exporter les constats affichés' });
    expect(within(dialog).getByText(/conservé nulle part/)).toBeVisible();
    expect(within(dialog).getByRole('button', { name: 'Télécharger' })).toBeVisible();
  });
});

describe('Keyboard use of the new controls (brief §31.1)', () => {
  it('switches the view, unfolds the details and the concentration with the keyboard', async () => {
    mockApi(async () =>
      json({ ...THREE, concentration_state: 'NOT_APPLICABLE', concentration: null }),
    );
    renderApp();
    await deposit();
    await screen.findByText('3 of 3 findings shown');

    screen.getByRole('button', { name: 'Expert view' }).focus();
    await userEvent.keyboard('{Enter}');
    expect(screen.getByText('Expert advice on B_05.01')).toBeInTheDocument();
    expect(screen.queryByText('Official major on B_05.01')).not.toBeInTheDocument();

    screen.getByText('Expert advice on B_05.01').closest('button')!.focus();
    await userEvent.keyboard('{Enter}');
    const details = screen.getByRole('button', { name: /Technical details/ });
    details.focus();
    await userEvent.keyboard(' ');
    expect(details).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText(/B_05\.01 · row 7 · c0010/)).toBeVisible();

    screen.getByRole('button', { name: /Concentration indicators/ }).focus();
    await userEvent.keyboard('{Enter}');
    expect(screen.getByText(/no row in B_02\.02/)).toBeVisible();
  });

  it('chooses a severity with the arrows and opens and closes the export with the keyboard', async () => {
    mockApi(async () => json(THREE));
    renderApp();
    await deposit();
    await screen.findByText('3 of 3 findings shown');

    screen.getByLabelText('Severity').focus();
    await userEvent.keyboard('{ArrowDown}');
    await screen.findByRole('listbox');
    await userEvent.keyboard('{ArrowDown}{ArrowDown}{Enter}');
    expect(await screen.findByText('1 of 3 findings shown')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('listbox')).not.toBeInTheDocument());
    expect(screen.getByText('Official major on B_05.01')).toBeInTheDocument();

    screen.getByRole('button', { name: 'Export the findings' }).focus();
    await userEvent.keyboard('{Enter}');
    const dialog = screen.getByRole('dialog', { name: 'Export the findings shown' });
    // The focus is kept inside the dialog while it is open.
    expect(dialog.contains(document.activeElement)).toBe(true);
    await userEvent.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });
});
