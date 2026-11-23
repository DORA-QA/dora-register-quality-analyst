// SPDX-License-Identifier: EUPL-1.2
import { API_URL } from '../config';

/** A source of the checks (mirrors `contracts/about.py`). */
export interface AboutSource {
  id: string;
  title?: string | null;
  url?: string | null;
  published?: string | null;
  sha256?: string | null;
}

/** Response of `GET /about` (mirrors `contracts/about.py` in the backend). */
export interface AboutInfo {
  version: string;
  taxonomy_version: string;
  catalog_codes: number;
  catalog_fingerprint: string;
  sources: AboutSource[];
  legal_notice?: string | null;
  licence?: string | null;
}

/** Calls the « About the engine » endpoint. Rejects if the API is unreachable. */
export async function fetchAbout(): Promise<AboutInfo> {
  const response = await fetch(`${API_URL}/about`, { signal: AbortSignal.timeout(5000) });
  if (!response.ok) throw new Error(`The API answered with HTTP ${response.status}.`);
  return (await response.json()) as AboutInfo;
}
