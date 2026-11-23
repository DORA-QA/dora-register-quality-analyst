// SPDX-License-Identifier: EUPL-1.2
import { API_URL } from '../config';

/** Response of `GET /api/gleif/status` (mirrors `contracts/health.py`, branch gleif-local). */
export interface GleifStatus {
  /** UPDATING: the GLEIF copy is being downloaded, no register is accepted meanwhile. */
  state: 'UPDATING' | 'READY' | 'UNAVAILABLE' | 'DISABLED';
  release?: string | null;
  /** Date and time of the GLEIF publication of the installed copy (UTC). */
  content_date?: string | null;
  received_bytes?: number;
  total_bytes?: number;
  last_error?: string | null;
}

const STATES = new Set(['UPDATING', 'READY', 'UNAVAILABLE', 'DISABLED']);
const TIMEOUT_MS = 5000;

/** Reads the state of the local GLEIF copy. Rejects if the API does not answer as expected. */
export async function fetchGleifStatus(): Promise<GleifStatus> {
  const response = await fetch(`${API_URL}/api/gleif/status`, {
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  if (!response.ok) throw new Error(`The API answered with HTTP ${response.status}.`);
  const body = (await response.json()) as Partial<GleifStatus>;
  if (typeof body.state !== 'string' || !STATES.has(body.state)) {
    throw new Error('The API answered with an unexpected GLEIF status.');
  }
  return body as GleifStatus;
}
