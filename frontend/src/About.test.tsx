// SPDX-License-Identifier: EUPL-1.2
/** « About the engine » and local status in the header (Sprint 4, §22 and §23). */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { AboutInfo } from './api/about';
import { json, mockApi, renderApp } from './test/app';

const ABOUT: AboutInfo = {
  version: '0.8.9',
  taxonomy_version: '4.0',
  catalog_codes: 155,
  catalog_fingerprint: 'abcdef123456',
  sources: [
    { id: 'dora', url: 'https://eur-lex.europa.eu/eli/reg/2022/2554/oj' },
    {
      id: 'eba_rules',
      title: 'EBA, list of validation rules',
      url: 'https://www.eba.europa.eu/rules.xlsx',
      published: '2026-10',
      sha256: '38c190fa4c2ff81f22a5bd2ed94f744fc64e4eb9b722676e07f89669d79b1aea',
    },
  ],
  legal_notice: null,
  licence: 'EUPL-1.2 (European Union Public Licence v. 1.2)',
};

describe('About the engine', () => {
  it('shows the local status in the header', () => {
    mockApi(async () => json(ABOUT));
    renderApp();

    expect(screen.getByText('Local analysis · no data sent')).toBeInTheDocument();
  });

  it('lists the engine, the sources, the score warning, the disclaimer and the licence', async () => {
    mockApi(async (url) => (url.endsWith('/about') ? json(ABOUT) : json({}, 500)));
    renderApp();

    await userEvent.click(screen.getByRole('button', { name: 'About the engine' }));
    const dialog = await screen.findByRole('dialog', { name: 'About the engine' });

    expect(await within(dialog).findByText('Version 0.8.9')).toBeInTheDocument();
    expect(within(dialog).getByText('EBA DORA taxonomy 4.0')).toBeInTheDocument();
    expect(
      within(dialog).getByText('Catalogue of 155 findings · fingerprint abcdef123456'),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByRole('link', { name: 'Regulation (EU) 2022/2554 (DORA)' }),
    ).toHaveAttribute('href', 'https://eur-lex.europa.eu/eli/reg/2022/2554/oj');
    expect(within(dialog).getByText(/SHA-256 38c190fa4c2f/)).toBeInTheDocument();
    expect(within(dialog).getByText(/without regulatory value/)).toBeInTheDocument();
    expect(within(dialog).getByText(/provided "as is", without warranty/)).toBeVisible();
    expect(within(dialog).getByText(/^EUPL-1.2/)).toBeVisible();
  });

  it('says so when the engine cannot be read', async () => {
    mockApi(async () => json({}, 500));
    renderApp();

    await userEvent.click(screen.getByRole('button', { name: 'About the engine' }));

    expect(await screen.findByText(/could not be read/)).toBeInTheDocument();
  });
});
