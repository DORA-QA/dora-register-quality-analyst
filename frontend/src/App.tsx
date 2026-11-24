// SPDX-License-Identifier: EUPL-1.2
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import { useState } from 'react';

import type { ImportFailure } from './api/imports';
import { AboutDialog } from './components/AboutDialog';
import { BackendStatus } from './components/BackendStatus';
import { DisclaimerDialog } from './components/DisclaimerDialog';
import { GleifFailure, GleifInfo, GleifSplash } from './components/GleifSplash';
import { ImportResult } from './components/ImportResult';
import { LanguageSelector } from './components/LanguageSelector';
import { Reassurance } from './components/Reassurance';
import { UploadPanel } from './components/UploadPanel';
import { API_URL, APP_NAME, APP_VERSION } from './config';
import { useBackendHealth } from './hooks/useBackendHealth';
import { useGleifStatus } from './hooks/useGleifStatus';
import { useImport } from './hooks/useImport';
import type { Dictionary } from './i18n/en';
import { format, useI18n } from './i18n/context';

function explain(failure: ImportFailure, t: Dictionary): string {
  if (failure.kind === 'network') return format(t.errors.network, { url: API_URL });
  return failure.detail ?? format(t.errors.http, { status: failure.status ?? '' });
}

/** ``disclaimerAccepted`` is only set by the tests; the user always sees the disclaimer first. */
export function App({ disclaimerAccepted = false }: { disclaimerAccepted?: boolean }) {
  const { language, t } = useI18n();
  const { health, checkAgain } = useBackendHealth();
  const { current, start, reset } = useImport(language);
  const gleif = useGleifStatus();
  const [accepted, setAccepted] = useState(disclaimerAccepted);

  if (gleif.state === 'UPDATING') return <GleifSplash status={gleif} />;

  return (
    <>
      {!accepted && <DisclaimerDialog onAccept={() => setAccepted(true)} />}
      <Container component="main" maxWidth="md" sx={{ py: { xs: 5, sm: 8 } }}>
        <Box
          component="header"
          sx={{
            mb: { xs: 3, sm: 4 },
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 2,
          }}
        >
          <Box>
            <Typography variant="h1">{APP_NAME}</Typography>
            <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
              <Typography color="text.secondary">
                {format(t.app.version, { version: APP_VERSION })}
              </Typography>
              <Chip size="small" variant="outlined" color="success" label={t.app.local} />
              <AboutDialog />
            </Box>
            <Box sx={{ mt: 1 }}>
              <BackendStatus health={health} onCheckAgain={checkAgain} />
              {gleif.state !== 'checking' && gleif.state !== 'unknown' && (
                <GleifInfo status={gleif} />
              )}
            </Box>
          </Box>
          <LanguageSelector />
        </Box>

        {gleif.state !== 'checking' && gleif.state !== 'unknown' && <GleifFailure status={gleif} />}

        {current.state !== 'done' && (
          <UploadPanel
            runningFileName={current.state === 'running' ? current.fileName : null}
            onFile={start}
          />
        )}
        {current.state === 'idle' && <Reassurance />}

        {current.state === 'error' && (
          <Alert severity="error" variant="outlined" sx={{ mt: 3 }}>
            {format(t.errors.importFailed, { name: current.fileName })}{' '}
            {explain(current.failure, t)}
          </Alert>
        )}
        {current.state === 'done' && <ImportResult result={current.result} onRestart={reset} />}
      </Container>
    </>
  );
}
