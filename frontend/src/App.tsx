// SPDX-License-Identifier: EUPL-1.2
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';

import type { ImportFailure } from './api/imports';
import { AboutDialog } from './components/AboutDialog';
import { BackendStatus } from './components/BackendStatus';
import { DemoBanner } from './components/DemoBanner';
import { GleifInfo, GleifSplash } from './components/GleifSplash';
import { ImportResult } from './components/ImportResult';
import { LanguageSelector } from './components/LanguageSelector';
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

export function App() {
  const { language, t } = useI18n();
  const { health, checkAgain } = useBackendHealth();
  const { current, start, reset } = useImport(language);
  const gleif = useGleifStatus();

  if (gleif.state === 'UPDATING') return <GleifSplash status={gleif} />;

  return (
    <>
      <DemoBanner />
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

        {current.state !== 'done' && (
          <UploadPanel
            runningFileName={current.state === 'running' ? current.fileName : null}
            onFile={start}
          />
        )}
        {/* Demo build: the "your register stays with you" block is hidden, real data is not welcome. */}

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
