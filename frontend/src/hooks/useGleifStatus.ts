// SPDX-License-Identifier: EUPL-1.2
import { useEffect, useState } from 'react';

import { fetchGleifStatus, type GleifStatus } from '../api/gleif';

export type GleifView = { state: 'checking' } | { state: 'unknown' } | GleifStatus;

/** Delay between two readings while the copy is being updated. */
export const POLL_MS = 2000;
/** Delay before asking again when the API does not answer yet (both containers start together). */
const RETRY_MS = 3000;
const MAX_RETRIES = 20;

/**
 * State of the local GLEIF copy. Read at start-up, then every POLL_MS while it is UPDATING, so
 * that the waiting screen closes by itself when the update is finished.
 */
export function useGleifStatus(): GleifView {
  const [view, setView] = useState<GleifView>({ state: 'checking' });

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let failures = 0;

    const read = () => {
      fetchGleifStatus()
        .then((status) => {
          if (cancelled) return;
          failures = 0;
          setView(status);
          if (status.state === 'UPDATING') timer = setTimeout(read, POLL_MS);
        })
        .catch(() => {
          if (cancelled) return;
          failures += 1;
          setView((current) => (current.state === 'UPDATING' ? current : { state: 'unknown' }));
          if (failures < MAX_RETRIES) timer = setTimeout(read, RETRY_MS);
        });
    };
    read();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  return view;
}
