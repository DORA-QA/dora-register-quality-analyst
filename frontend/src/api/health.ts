// SPDX-License-Identifier: EUPL-1.2
import { API_URL } from '../config';

/** Response of `GET /health` (mirrors `contracts/health.py` in the backend). */
export interface HealthStatus {
  status: 'ok';
  version: string;
  /** EBA taxonomy checked against (since 0.8.4). */
  taxonomy_version?: string | null;
}

const TIMEOUT_MS = 5000;

/** Calls the backend health endpoint. Rejects if the API is unreachable or unhealthy. */
export async function fetchHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_URL}/health`, {
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });

  if (!response.ok) {
    throw new Error(`The API answered with HTTP ${response.status}.`);
  }

  const body = (await response.json()) as Partial<HealthStatus>;
  if (body.status !== 'ok' || typeof body.version !== 'string') {
    throw new Error('The API answered with an unexpected health payload.');
  }

  return {
    status: body.status,
    version: body.version,
    taxonomy_version: body.taxonomy_version ?? null,
  };
}
