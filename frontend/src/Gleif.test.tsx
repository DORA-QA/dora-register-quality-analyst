// SPDX-License-Identifier: EUPL-1.2
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

  it('explains a failed update after the waiting screen, without a copy', async () => {
    mockGleif(
      { state: 'UPDATING', received_bytes: 0, total_bytes: 0 },
      { state: 'UNAVAILABLE', last_error: 'network' },
    );
    renderApp();

    await screen.findByRole('dialog', { name: 'Online update in progress' });
    const alert = await screen.findByRole('alert', {}, { timeout: 4000 });
    expect(alert).toHaveTextContent('The online update of the GLEIF copy failed');
    expect(alert).toHaveTextContent('could not reach GitHub');
    expect(alert).toHaveTextContent('the GLEIF checks will not be performed');
    expect(alert).toHaveTextContent('api.github.com');
    expect(alert).toHaveTextContent('Code: network');
    expect(screen.getByLabelText('Register file')).toBeInTheDocument();
  });

  it('says which copy is used when the update fails but a copy is installed', async () => {
    mockGleif({
      state: 'READY',
      release: 'gleif-20261108-0900',
      content_date: '2026-11-08T09:00:01Z',
      last_error: 'checksum',
    });
    renderApp();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('wrong fingerprint');
    expect(alert).toHaveTextContent('uses the copy already installed, dated 2026-11-08');
    expect(alert).not.toHaveTextContent('api.github.com');
    await userEvent.click(within(alert).getByRole('button', { name: /close/i }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('gives a generic reason for an unknown error code', async () => {
    mockGleif({ state: 'UNAVAILABLE', last_error: 'something_new' });
    renderApp();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'An unexpected error occurred during the update.',
    );
  });

  it('shows no failure message when the update succeeded', async () => {
    mockGleif({ state: 'READY', content_date: '2026-11-08T09:00:01Z' });
    renderApp();
    await screen.findByText('GLEIF: copy of 2026-11-08');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('Offline version', () => {
  it('says on the home screen that the GLEIF checks are not available', async () => {
    mockApi(async () => json(FAILED_IMPORT));
    renderApp();
    expect(await screen.findByText(/checks not available in this offline version/)).toBeVisible();
  });
});
