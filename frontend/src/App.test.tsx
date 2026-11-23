// SPDX-License-Identifier: EUPL-1.2
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import pkg from '../package.json';

import type { ImportResponse } from './api/imports';
import {
  deposit,
  FAILED_IMPORT,
  FAILED_IMPORT_FR,
  HEALTH,
  json,
  mockApi,
  renderApp,
} from './test/app';

describe('App', () => {
  it('starts and shows the product name, version and backend status', async () => {
    mockApi(async () => json(FAILED_IMPORT));

    renderApp();

    expect(screen.getByRole('heading', { name: 'DORA QA' })).toBeInTheDocument();
    expect(screen.getByText(`Version ${pkg.version}`)).toBeInTheDocument();
    expect(await screen.findByText('OK')).toBeInTheDocument();
    expect(screen.getByText(/API version 0\.8\.3 · EBA taxonomy 4\.0/)).toBeInTheDocument();
  });

  it('explains what to do when the backend does not answer, and can check again', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed'));

    renderApp();

    expect(await screen.findByText('Unreachable')).toBeInTheDocument();

    fetchMock.mockResolvedValue(json(HEALTH));
    await userEvent.click(screen.getByRole('button', { name: 'Check again' }));

    expect(await screen.findByText('OK')).toBeInTheDocument();
  });

  it('sends the deposited file and shows the result of the import', async () => {
    const fetchMock = mockApi(async () => json(FAILED_IMPORT));
    renderApp();

    await deposit();

    const result = await screen.findByRole('region', { name: 'Import result' });
    expect(within(result).getByText(/^Import:/)).toHaveTextContent('Import: Failed');
    expect(within(result).getByText(/14 tables · 1,234 rows · 1 blocker · 0 majors/)).toBeVisible();
    expect(within(result).getByText('DUMMYLEI123456789012')).toBeInTheDocument();
    expect(within(result).getByText('Missing templates: B_99.01')).toBeInTheDocument();

    const [url, options] = fetchMock.mock.calls.at(-1)!;
    expect(url).toBe('http://localhost:8000/api/import?lang=en');
    expect((options!.body as FormData).get('file')).toBeInstanceOf(File);
    // Review S6: the API refuses an import without this header.
    expect(options!.headers).toEqual({ 'X-ROI-Client': 'roi-quality-engine-web' });
  });

  it('unfolds a finding to its explanation, fix and advice, the source and codes folded below', async () => {
    mockApi(async () => json(FAILED_IMPORT));
    renderApp();
    await deposit();

    await userEvent.click(await screen.findByText(/Template B_99.01 is missing/));

    expect(screen.getByText('BLOCKER · PKG-010 · provisional severity')).toBeInTheDocument();
    expect(screen.getByText(/must all be present/)).toBeVisible();
    expect(screen.getByText(/Add the file b_99.01.csv/)).toBeVisible();
    expect(screen.getByText('Expert advice')).toBeVisible();
    expect(screen.getByText(/Many tools skip a template/)).toBeVisible();
    expect(screen.queryByText('Official guidance')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Technical details/ }));
    expect(screen.getByText('Official guidance')).toBeVisible();
    expect(screen.getByText('EBA.808')).toBeVisible();
  });

  it('filters the findings by severity and shows where each one occurs', async () => {
    const withPlaces: ImportResponse = {
      ...FAILED_IMPORT,
      counts: { blocker: 1, major: 1, minor: 0, info: 0 },
      messages: [
        {
          ...FAILED_IMPORT.messages[0],
          occurrences: [{ table: 'B_01.01', row: 3, column: 'c0010', value: 'abc' }],
          occurrences_total: 40,
        },
        {
          ...FAILED_IMPORT.messages[0],
          code: 'DAT-099',
          severity: 'MAJOR',
          message: 'Second finding',
        },
      ],
    };
    mockApi(async () => json(withPlaces));
    renderApp();
    await deposit();

    expect(await screen.findByText('2 of 2 findings shown')).toBeInTheDocument();
    await userEvent.click(screen.getByText(/Template B_99.01 is missing/));
    expect(screen.queryByText(/B_01\.01 · row 3 · c0010/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Technical details/ }));
    expect(screen.getByText(/B_01\.01 · row 3 · c0010 · .*abc/)).toBeVisible();
    expect(screen.getByText(/First 1 of 40/)).toBeVisible();

    await userEvent.click(screen.getByLabelText('Severity'));
    await userEvent.click(await screen.findByRole('option', { name: 'MAJOR' }));

    expect(screen.getByText('1 of 2 findings shown')).toBeInTheDocument();
    expect(screen.getByText('Second finding')).toBeInTheDocument();
    expect(screen.queryByText(/Template B_99.01 is missing/)).not.toBeInTheDocument();
  });

  it('filters the findings by origin and by status of the severity (CL-42)', async () => {
    mockApi(async () =>
      json({
        ...FAILED_IMPORT,
        messages: [
          { ...FAILED_IMPORT.messages[0], origin: 'OFFICIAL', severity_status: 'CONFIRMED' },
          {
            ...FAILED_IMPORT.messages[0],
            code: 'REL-009',
            message: 'Expert finding',
            origin: 'PO_VALIDATED',
            severity_status: 'PO_VALIDATED',
          },
        ],
      }),
    );
    renderApp();
    await deposit();

    expect(await screen.findByText('2 of 2 findings shown')).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Origin'));
    await userEvent.click(await screen.findByRole('option', { name: 'expert check' }));
    expect(screen.getByText('1 of 2 findings shown')).toBeInTheDocument();
    expect(screen.getByText('Expert finding')).toBeInTheDocument();

    await userEvent.click(screen.getByLabelText('Status'));
    await userEvent.click(await screen.findByRole('option', { name: 'provisional severity' }));
    expect(screen.getByText('0 of 2 findings shown')).toBeInTheDocument();
  });

  it('shows the origin of a cross-table finding and where the value was expected', async () => {
    const crossTable: ImportResponse = {
      ...FAILED_IMPORT,
      messages: [
        {
          ...FAILED_IMPORT.messages[0],
          severity_status: 'PO_VALIDATED',
          origin: 'PO_VALIDATED',
          occurrences: [
            {
              table: 'B_02.02',
              row: 4,
              column: 'c0040',
              value: 'eba_qCO:qx2003',
              target_table: 'B_05.01',
              target_column: 'c0020',
              side: 'source',
            },
          ],
          occurrences_total: 1,
        },
      ],
    };
    mockApi(async () => json(crossTable));
    renderApp();
    await deposit();

    expect(
      await screen.findByText(
        'BLOCKER · PKG-010 · severity set by the project experts · expert check',
      ),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByText(/Template B_99.01 is missing/));
    await userEvent.click(screen.getByRole('button', { name: /Technical details/ }));
    expect(screen.getByText(/c0040 · .*qx2003.* · expected in B_05\.01 · c0020/)).toBeVisible();
  });

  it('says when the EBA publishes the rule as a warning and folds the technical details', async () => {
    const warning: ImportResponse = {
      ...FAILED_IMPORT,
      messages: [
        {
          ...FAILED_IMPORT.messages[0],
          code: 'DAT-024',
          severity: 'MAJOR',
          eba_severity: 'warning',
          official_codes: ['EBA.V8825'],
        },
      ],
    };
    mockApi(async () => json(warning));
    renderApp();
    await deposit();

    expect(await screen.findByText(/MAJOR · DAT-024 · EBA warning/)).toBeInTheDocument();
    await userEvent.click(screen.getByText(/Template B_99.01 is missing/));
    expect(screen.queryByText('EBA.V8825')).not.toBeInTheDocument();
    const toggle = screen.getByRole('button', { name: /Technical details/ });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(toggle);
    expect(screen.getByText('EBA.V8825')).toBeVisible();
  });

  it('reads every occurrence of a finding beyond the first 25 and exports them (#183)', async () => {
    const place = (row: number) => ({ table: 'B_05.01', row, column: 'c0010', value: `P${row}` });
    const many: ImportResponse = {
      ...FAILED_IMPORT,
      messages: [
        {
          ...FAILED_IMPORT.messages[0],
          code: 'DQ-004',
          index: 0,
          occurrences: Array.from({ length: 25 }, (_, i) => place(i + 1)),
          occurrences_total: 136,
          occurrences_available: 136,
        },
      ],
    };
    const fetchMock = mockApi(async (url) =>
      url.includes('/occurrences')
        ? json({
            import_id: many.import_id,
            index: 0,
            code: 'DQ-004',
            matching: 136,
            offset: 0,
            limit: 1000,
            occurrences: Array.from({ length: 136 }, (_, i) => place(i + 1)),
            occurrences_total: 136,
            occurrences_available: 136,
          })
        : json(many),
    );
    renderApp();
    await deposit();

    await userEvent.click(await screen.findByText(/Template B_99.01 is missing/));
    await userEvent.click(screen.getByRole('button', { name: /Technical details/ }));
    expect(screen.queryByText(/row 136 /)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Show all 136' }));

    expect(await screen.findByText(/B_05\.01 · row 136 · c0010/)).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Show all 136' })).not.toBeInTheDocument();
    const [url] = fetchMock.mock.calls.at(-1)!;
    expect(String(url)).toContain(
      `/api/import/${many.import_id}/findings/0/occurrences?offset=0&limit=1000`,
    );
  });

  it('exports the findings shown after a confidentiality warning (Sprint 4, lot 3)', async () => {
    mockApi(async () =>
      json({ ...FAILED_IMPORT, messages: [{ ...FAILED_IMPORT.messages[0], index: 0 }] }),
    );
    const clicked: string[] = [];
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clicked.push(this.href);
    });
    renderApp();
    await deposit();

    await userEvent.click(await screen.findByRole('button', { name: 'Export the findings' }));
    const dialog = screen.getByRole('dialog', { name: 'Export the findings shown' });
    expect(within(dialog).getByText(/kept nowhere by the application/)).toBeVisible();
    await userEvent.click(within(dialog).getByLabelText('JSON Lines'));
    await userEvent.click(within(dialog).getByLabelText('Leave out the values from the register'));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Download' }));

    expect(clicked).toHaveLength(1);
    const url = new URL(clicked[0]);
    expect(url.pathname).toBe(`/api/import/${FAILED_IMPORT.import_id}/export.jsonl`);
    expect(url.searchParams.get('values')).toBe('false');
    expect(url.searchParams.get('findings')).toBe('0');
    expect(url.searchParams.get('lang')).toBe('en');
    click.mockRestore();
  });

  it('shows the concentration indicators, folded, without any finding (CL-43)', async () => {
    const share = (key: string, label: string, value: number) => ({
      key,
      rows: 1,
      share: value,
      providers: null,
      label,
    });
    mockApi(async () =>
      json({
        ...FAILED_IMPORT,
        concentration_state: 'EVALUATED',
        concentration: {
          basis: 'B_02.02',
          rows: 17,
          providers_count: 6,
          hhi: 2872,
          providers: [
            {
              code: 'LEI1',
              code_type: 'eba_qCO:qx2000',
              name: 'PSEUDO PROVIDER A',
              rows: 8,
              share: 0.4706,
              critical_functions: 2,
              critical_share: 1,
            },
          ],
          providers_not_shown: 0,
          critical_functions: 2,
          critical_functions_without_provider: 0,
          single_provider_critical_functions: [{ function: 'F1', entity: 'E1', provider: 'LEI1' }],
          single_provider_not_shown: 0,
          by_headquarters_country: { items: [share('eba_GA:FR', 'FRANCE', 0.94)], not_shown: 0 },
          by_provision_country: { items: [], not_shown: 0 },
          by_service_type: {
            items: [share('eba_TA:S14', 'ICT operation management', 0.35)],
            not_shown: 0,
          },
          notes: [],
        },
      }),
    );
    renderApp();
    await deposit();

    const summary = await screen.findByRole('button', { name: /Concentration indicators/ });
    expect(screen.queryByText(/PSEUDO PROVIDER A/)).not.toBeInTheDocument();
    await userEvent.click(summary);
    expect(screen.getByText(/6 direct provider\(s\) over 17 rows/)).toBeVisible();
    expect(screen.getByText(/PSEUDO PROVIDER A · 47.1 % · 2 critical/)).toBeVisible();
    expect(screen.getByText(/rest on a single direct provider: F1 \(LEI1\)/)).toBeVisible();
    expect(screen.getByText('ICT operation management · 35 %')).toBeVisible();
    expect(screen.getByText(/never produce a finding/)).toBeVisible();
  });

  it('tells the user when the file is refused or the API does not answer', async () => {
    mockApi(async () => json({ detail: 'The file exceeds the limit of 100 MB.' }, 413));
    renderApp();

    await deposit('Register file', 'huge.zip');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'huge.zip could not be imported. The file exceeds the limit of 100 MB.',
    );
  });
});

describe('Check report', () => {
  it('shows the counts, the three scores and how they are calculated (CL-22)', async () => {
    const score = (scope: 'REGULATORY' | 'QUALITY', value: number | null) => ({
      scope,
      value,
      state: value === null ? ('NOT_EVALUATED' as const) : ('EVALUATED' as const),
      weight_earned: 8.5,
      weight_total: 13,
      checks_performed: 5,
      passed: 3,
      warnings: 1,
      failed: 1,
      not_run: value === null ? ['ENV'] : [],
      not_evaluated: [],
      not_applicable: [],
      origins: [],
      categories: [],
      severities: [],
      provisional_codes: 1,
      provisional_findings: 2,
    });
    mockApi(async () =>
      json({
        ...FAILED_IMPORT,
        scores: {
          regulatory: score('REGULATORY', 88),
          quality: score('QUALITY', null),
          confidence: { value: 0, state: 'EVALUATED', not_run: [] },
          computed_at: '2026-11-04T22:00:00+00:00',
          engine_version: '0.8.4',
        },
      }),
    );
    renderApp();
    await deposit();

    const result = await screen.findByRole('region', { name: 'Import result' });
    expect(within(result).getByText('Checks performed')).toBeVisible();
    expect(within(result).getByText('Regulatory score: 88/100')).toBeVisible();
    // A score that could not be computed is never shown as 0.
    expect(within(result).getByText('Quality score: not evaluated')).toBeVisible();
    expect(within(result).getByText('Checks that could not be carried out: ENV.')).toBeVisible();
    expect(within(result).getByText('Confidence: 0/100')).toBeVisible();
    expect(within(result).getAllByText('Includes 2 findings from provisional rules.')).toHaveLength(
      2,
    );
    expect(within(result).getByText(/without regulatory value/)).toBeVisible();
    expect(within(result).queryByText(/Each check weighs/)).not.toBeInTheDocument();
    await userEvent.click(within(result).getByRole('button', { name: /How are these scores/ }));
    expect(within(result).getByText(/Each check weighs/)).toBeVisible();
  });

  it('shows the plain-language overview written by the engine (CL-37)', async () => {
    mockApi(async () =>
      json({
        ...FAILED_IMPORT,
        overview: {
          verdict: 'BLOCKED',
          headline: 'The register cannot be filed as it is: 1 blocking finding(s).',
          figures: 'Regulatory score: 88/100; quality score: 89/100. 1 finding(s).',
          tables: "The findings are concentrated on 'List of branches' (B_01.03) (1 finding(s)).",
          gleif: 'GLEIF check (copy of 2026-11-08): 12 LEI checked; 7 LEI not found.',
          priorities: [
            {
              index: 0,
              code: 'PKG-010',
              severity: 'BLOCKER',
              finding: 'Template B_99.01 is missing.',
              action: 'Add the file b_99.01.csv.',
            },
          ],
          profiles: '1 finding(s) come from official rules, 0 from expert advice.',
          note: 'Overview produced automatically from the findings, without artificial intelligence.',
        },
      }),
    );
    renderApp();
    await deposit();

    const overview = await screen.findByRole('region', { name: 'In short' });
    expect(within(overview).getByText(/cannot be filed as it is/)).toBeVisible();
    expect(within(overview).getByText('Priorities')).toBeVisible();
    expect(within(overview).getByText('BLOCKER · PKG-010')).toBeVisible();
    expect(within(overview).getByText('Add the file b_99.01.csv.')).toBeVisible();
    expect(within(overview).getByText(/GLEIF check \(copy of 2026-11-08\)/)).toBeVisible();
    expect(within(overview).getByText(/without artificial intelligence/)).toBeVisible();
  });

  it('switches between all findings, the regulatory view and the expert view (CL-22)', async () => {
    mockApi(async () =>
      json({
        ...FAILED_IMPORT,
        messages: [
          { ...FAILED_IMPORT.messages[0], profile: 'REGULATORY' },
          {
            ...FAILED_IMPORT.messages[0],
            code: 'DQ-004',
            severity: 'INFO',
            message: 'Unused provider',
            profile: 'EXPERT',
          },
        ],
      }),
    );
    renderApp();
    await deposit();

    expect(await screen.findByText('2 of 2 findings shown')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Regulatory view' }));
    expect(screen.getByText(/1 of 2 findings shown · 1 more expert advice/)).toBeInTheDocument();
    expect(screen.queryByText('Unused provider')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Expert view' }));
    expect(screen.getByText('Unused provider')).toBeInTheDocument();
    expect(screen.getByText(/never a regulatory non-compliance/)).toBeVisible();
  });

  it('lists the checks by category and can show only those that failed', async () => {
    mockApi(async () => json(FAILED_IMPORT));
    renderApp();
    await deposit();

    expect(await screen.findByText('The file is an XML or a ZIP')).toBeVisible();
    expect(screen.queryByText('Delivery envelope recognised')).not.toBeInTheDocument();
    expect(screen.getByText('FilingIndicators: valid values')).toBeVisible();

    await userEvent.click(screen.getByRole('switch', { name: /Show only failed/ }));

    expect(screen.queryByText('The file is an XML or a ZIP')).not.toBeInTheDocument();
    expect(screen.getByText('All 15 tables are present')).toBeVisible();
  });

  it('goes back to the deposit screen when the validator is restarted', async () => {
    mockApi(async () => json(FAILED_IMPORT));
    renderApp();
    await deposit();
    await screen.findByRole('region', { name: 'Import result' });

    await userEvent.click(screen.getByRole('button', { name: 'Restart the validator' }));

    expect(screen.getByRole('button', { name: 'Choose a file' })).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Import result' })).not.toBeInTheDocument();
    expect(screen.getByText('Your register stays with you')).toBeVisible();
  });
});

describe('Disclaimer', () => {
  it('blocks the interface until the disclaimer is ticked and confirmed', async () => {
    mockApi(async () => json(FAILED_IMPORT));
    renderApp({ disclaimerAccepted: false });

    const dialog = screen.getByRole('dialog', { name: 'Disclaimer' });
    expect(within(dialog).getByText(/provided "as is", without warranty/)).toBeVisible();
    const proceed = within(dialog).getByRole('button', { name: 'Continue' });
    expect(proceed).toBeDisabled();

    await userEvent.keyboard('{Escape}');
    expect(screen.getByRole('dialog', { name: 'Disclaimer' })).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole('checkbox'));
    await userEvent.click(proceed);
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(screen.getByText('Your register stays with you')).toBeVisible();
  });

  it('is translated and keeps nothing in the browser storage', async () => {
    mockApi(async () => json(FAILED_IMPORT));
    localStorage.clear();
    sessionStorage.clear();
    renderApp({ disclaimerAccepted: false });

    await userEvent.click(screen.getByRole('button', { name: 'Français' }));
    const dialog = screen.getByRole('dialog', { name: 'Avertissement' });
    expect(within(dialog).getByText(/fourni « en l'état », sans garantie/)).toBeVisible();
    await userEvent.click(within(dialog).getByRole('checkbox'));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Continuer' }));

    const keys = [...Object.keys(localStorage), ...Object.keys(sessionStorage)];
    expect(keys.filter((key) => /disclaimer|avertissement/i.test(key))).toEqual([]);
  });
});

describe('Language', () => {
  it('switches the whole interface to French and remembers the choice', async () => {
    mockApi(async () => json(FAILED_IMPORT));
    const first = renderApp();
    expect(screen.getByRole('group', { name: 'Language' })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Français' }));

    expect(screen.getByText("Déposer un registre d'information")).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Choisir un fichier' })).toBeInTheDocument();
    expect(screen.getByText(/État du backend/)).toBeInTheDocument();
    expect(document.documentElement.lang).toBe('fr');

    first.unmount();
    renderApp();
    expect(screen.getByText("Déposer un registre d'information")).toBeInTheDocument();
  });

  it('displays the last import in the new language without sending the file again', async () => {
    const fetchMock = mockApi(async (url) =>
      json(url.includes('lang=fr') ? FAILED_IMPORT_FR : FAILED_IMPORT),
    );
    renderApp();
    await deposit();
    await screen.findByText(/Template B_99.01 is missing/);

    await userEvent.click(screen.getByRole('button', { name: 'Français' }));

    const result = await screen.findByRole('region', { name: "Résultat de l'import" });
    expect(await within(result).findByText(/Le modèle B_99.01 est manquant/)).toBeVisible();
    expect(
      within(result).getByText('BLOQUANT · PKG-010 · sévérité provisoire'),
    ).toBeInTheDocument();
    expect(within(result).getByText(/^Import\s:/)).toHaveTextContent(/Import\s: Échec/);
    expect(
      within(result).getByText(/14 tables · 1\s234 lignes · 1 bloquant · 0 majeur ·/),
    ).toBeVisible();
    expect(within(result).getByText(/FR All 15 tables are present/)).toBeInTheDocument();

    const [url, options] = fetchMock.mock.calls.at(-1)!;
    expect(url).toBe('http://localhost:8000/api/import/abc?lang=fr');
    // A GET without body: the file is not sent again. The client header goes with every call.
    expect(options?.method).toBeUndefined();
    expect(options?.body).toBeUndefined();
    expect(options?.headers).toEqual({ 'X-ROI-Client': 'roi-quality-engine-web' });
  });

  it('asks the API for French findings when a file is deposited in French', async () => {
    const fetchMock = mockApi(async () => json(FAILED_IMPORT_FR));
    renderApp();
    await userEvent.click(screen.getByRole('button', { name: 'Français' }));

    await deposit('Fichier du registre');

    await screen.findByText(/Le modèle B_99.01 est manquant/);
    expect(fetchMock.mock.calls.at(-1)![0]).toBe('http://localhost:8000/api/import?lang=fr');
  });
});
