// SPDX-License-Identifier: EUPL-1.2
import { useCallback, useEffect, useState } from 'react';

import { fetchHealth } from '../api/health';

export type BackendHealth =
  | { state: 'checking' }
  | { state: 'ok'; version: string; taxonomy?: string | null }
  | { state: 'unreachable' };

/** Checks the backend on mount and exposes a function to check again. */
export function useBackendHealth(): { health: BackendHealth; checkAgain: () => void } {
  const [health, setHealth] = useState<BackendHealth>({ state: 'checking' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    fetchHealth()
      .then((result) => {
        if (!cancelled)
          setHealth({ state: 'ok', version: result.version, taxonomy: result.taxonomy_version });
      })
      .catch(() => {
        if (!cancelled) setHealth({ state: 'unreachable' });
      });

    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const checkAgain = useCallback(() => {
    setHealth({ state: 'checking' });
    setAttempt((current) => current + 1);
  }, []);

  return { health, checkAgain };
}
