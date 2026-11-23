// SPDX-License-Identifier: EUPL-1.2
import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { FAILED_IMPORT, HEALTH, json, mockApi, renderApp } from './test/app';

const MB = 1024 * 1024;

function mockGleif(...answers: object[]) {
  let call = 0;
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith('/health')) return json(HEALTH);
    if (url.endsWith('/api/gleif/status')) {
      const answer = answers[Math.min(call, answers.length - 1)];
      call += 1;
      return json(answer);
    }
    throw new Error(`unexpected call ${url}`);
  });
}

describe('GLEIF copy (branch gleif-local)', () => {
  it('covers the page while the copy is updated online, then opens the import', async () => {
    mockGleif(
      { state: 'UPDATING', received_bytes: 30 * MB, total_bytes: 120 * MB },
      { state: 'READY', release: 'gleif-20261108-0900', content_date: '2026-11-08T09:00:01Z' },
    );
    renderApp();

    const splash = await screen.findByRole('dialog', { name: 'Online update in progress' });
    expect(splash).toHaveTextContent('It cannot accept a register for the moment.');
    expect(splash).toHaveTextContent('30 MB of 120 MB (25 %)');
    expect(screen.queryByLabelText('Register file')).not.toBeInTheDocument();

    expect(
      await screen.findByLabelText('Register file', {}, { timeout: 4000 }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByText('GLEIF: copy of 2026-11-08')).toBeInTheDocument();
  });

  it('says when no copy is installed, without blocking the import', async () => {
    mockGleif({ state: 'UNAVAILABLE', last_error: 'no_access' });
    renderApp();

    expect(
      await screen.findByText(/no copy installed, the GLEIF checks will not be performed/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Register file')).toBeInTheDocument();
  });
});

describe('Offline version', () => {
  it('says on the home screen that the GLEIF checks are not available', async () => {
    mockApi(async () => json(FAILED_IMPORT));
    renderApp();
    expect(await screen.findByText(/checks not available in this offline version/)).toBeVisible();
  });
});
