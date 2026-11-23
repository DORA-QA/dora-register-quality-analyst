// SPDX-License-Identifier: EUPL-1.2
import { useCallback, useEffect, useState } from 'react';

import { fetchImport, ImportFailure, importRegister, type ImportResponse } from '../api/imports';

export type ImportState =
  | { state: 'idle' }
  | { state: 'running'; fileName: string }
  | { state: 'done'; result: ImportResponse }
  | { state: 'error'; fileName: string; failure: ImportFailure };

/**
 * Runs an import and keeps its result. A new import replaces the previous one.
 * When the language changes, the result is read again in the new language.
 */
export function useImport(language: string): {
  current: ImportState;
  start: (file: File) => void;
  /** Forgets the result and goes back to the deposit screen. */
  reset: () => void;
} {
  const [current, setCurrent] = useState<ImportState>({ state: 'idle' });

  const start = useCallback(
    (file: File) => {
      setCurrent({ state: 'running', fileName: file.name });
      importRegister(file, language)
        .then((result) => setCurrent({ state: 'done', result }))
        .catch((error: unknown) =>
          setCurrent({
            state: 'error',
            fileName: file.name,
            failure: error instanceof ImportFailure ? error : new ImportFailure('network'),
          }),
        );
    },
    [language],
  );

  const reset = useCallback(() => setCurrent({ state: 'idle' }), []);

  const shown = current.state === 'done' ? current.result : null;
  useEffect(() => {
    if (shown === null || shown.language === language) return;
    let cancelled = false;
    fetchImport(shown.import_id, language)
      .then((result) => {
        if (!cancelled) setCurrent({ state: 'done', result });
      })
      // The import may have expired: the result stays in its original language.
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [shown, language]);

  return { current, start, reset };
}
