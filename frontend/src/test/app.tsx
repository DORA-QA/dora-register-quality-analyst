// SPDX-License-Identifier: EUPL-1.2
/** Shared fixtures of the interface tests: a fake API, a sample import and the deposit gesture. */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import type { ImportResponse } from '../api/imports';
import { App } from '../App';
import { I18nProvider } from '../i18n/I18nProvider';

export const HEALTH = { status: 'ok', version: '0.8.3', taxonomy_version: '4.0' };
export const GLEIF_DISABLED = { state: 'DISABLED' };

export const FAILED_IMPORT: ImportResponse = {
  import_id: 'abc',
  language: 'en',
  status: 'FAILED',
  source_type: 'ZIP',
  tables_loaded: 14,
  rows_loaded: 1234,
  dataset_available: true,
  file_name: 'register.zip',
  metadata: {
    channel: null,
    package_name: 'pkg',
    taxonomy_version: '4.0',
    module_code: 'DORA010100',
    entity_lei: 'DUMMYLEI123456789012',
    reporting_scope: 'CON',
    country: 'FR',
    reference_date: '2025-12-31',
    base_currency: 'EUR',
    envelope_sender_lei: null,
    envelope_domain: null,
  },
  rt_detected: ['B_01.01'],
  missing_rt: ['B_99.01'],
  counts: { blocker: 1, major: 0, minor: 0, info: 0 },
  steps: [{ key: 'package_validation', name: 'Package validation', status: 'FAILED' }],
  tables: [{ code: 'B_01.01', file: 'b_01.01.csv', rows: 1, columns: 3 }],
  summary: {
    checks_performed: 3,
    passed: 1,
    warnings: 1,
    failed: 1,
    rows_analysed: 1234,
    score: 35,
    weight_earned: 8.5,
    weight_total: 13,
  },
  categories: [
    { key: 'file', name: 'File' },
    { key: 'indicators', name: 'Tables and filing indicators' },
  ],
  checks: [
    {
      id: 'file_type',
      category: 'file',
      name: 'The file is an XML or a ZIP',
      status: 'PASSED',
      codes: [],
    },
    {
      id: 'pkg_templates',
      category: 'indicators',
      name: 'All 15 tables are present',
      status: 'FAILED',
      codes: ['PKG-010'],
    },
    {
      id: 'pkg_indicator_values',
      category: 'indicators',
      name: 'FilingIndicators: valid values',
      status: 'WARNING',
      codes: ['PKG-022'],
    },
    {
      id: 'env_root',
      category: 'file',
      name: 'Delivery envelope recognised',
      status: 'SKIPPED',
      codes: [],
    },
  ],
  messages: [
    {
      code: 'PKG-010',
      severity: 'BLOCKER',
      message: 'Template B_99.01 is missing (b_99.01.csv not found).',
      details: null,
      explanation: 'The 15 templates of the register must all be present.',
      recommendation: 'Add the file b_99.01.csv with its header row.',
      expert_advice: 'Many tools skip a template when its sheet is empty.',
      reference: { type: 'official_guide', text: 'EBA technical checks', verified: true },
      official_codes: ['EBA.808'],
      check_id: 'pkg_templates',
      severity_status: 'PROVISIONAL',
    },
  ],
};

export const FAILED_IMPORT_FR: ImportResponse = {
  ...FAILED_IMPORT,
  language: 'fr',
  checks: FAILED_IMPORT.checks.map((c) => ({ ...c, name: `FR ${c.name}` })),
  messages: [
    {
      ...FAILED_IMPORT.messages[0],
      message: 'Le modèle B_99.01 est manquant (b_99.01.csv introuvable).',
      expert_advice: "Beaucoup d'outils ignorent un modèle quand son onglet est vide.",
    },
  ],
};

export function json(body: unknown, status = 200): Response {
  return { ok: status < 400, status, json: async () => body } as Response;
}

/** Answers the health check, and any import call with the given function. */
export function mockApi(importResponse: (url: string) => Promise<Response>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith('/health')) return json(HEALTH);
    if (url.endsWith('/api/gleif/status')) return json(GLEIF_DISABLED);
    return importResponse(url);
  });
}

export function renderApp() {
  return render(
    <I18nProvider>
      <App />
    </I18nProvider>,
  );
}

export async function deposit(label = 'Register file', name = 'register.zip') {
  const file = new File(['content'], name);
  await userEvent.upload(screen.getByLabelText(label), file);
}
