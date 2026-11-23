// SPDX-License-Identifier: EUPL-1.2
import Box from '@mui/material/Box';
import LinearProgress from '@mui/material/LinearProgress';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';

import type { GleifStatus } from '../api/gleif';
import { format, useI18n } from '../i18n/context';

const MB = 1024 * 1024;

/**
 * Waiting screen shown while the GLEIF copy is updated online (branch gleif-local). It covers the
 * whole page: the import is not available, and the API refuses a register meanwhile (HTTP 503).
 */
export function GleifSplash({ status }: { status: GleifStatus }) {
  const { t } = useI18n();
  const total = status.total_bytes ?? 0;
  const received = status.received_bytes ?? 0;
  const percent = total > 0 ? Math.min(100, Math.round((received / total) * 100)) : null;

  return (
    <Box
      role="dialog"
      aria-modal="true"
      aria-labelledby="gleif-splash-title"
      sx={{
        position: 'fixed',
        inset: 0,
        zIndex: (theme) => theme.zIndex.modal,
        bgcolor: 'background.default',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 3,
      }}
    >
      <Paper variant="outlined" sx={{ p: { xs: 3, sm: 5 }, maxWidth: 560, width: '100%' }}>
        <Typography id="gleif-splash-title" variant="h2" component="h2" gutterBottom>
          {t.gleif.splashTitle}
        </Typography>
        <Typography sx={{ mb: 1 }}>{t.gleif.splashBody}</Typography>
        <Typography sx={{ mb: 3, fontWeight: 600 }}>{t.gleif.splashNoImport}</Typography>
        <LinearProgress
          variant={percent === null ? 'indeterminate' : 'determinate'}
          value={percent ?? undefined}
          aria-label={t.gleif.splashTitle}
        />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }} aria-live="polite">
          {percent === null
            ? t.gleif.splashConnecting
            : format(t.gleif.progress, {
                received: (received / MB).toFixed(0),
                total: (total / MB).toFixed(0),
                percent,
              })}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          {t.gleif.splashCloses}
        </Typography>
      </Paper>
    </Box>
  );
}

/** One line under the backend status: date of the GLEIF copy, or why there is none. */
export function GleifInfo({ status }: { status: GleifStatus }) {
  const { t } = useI18n();
  if (status.state === 'DISABLED' || status.state === 'UPDATING') return null;
  const text =
    status.state === 'READY' && status.content_date
      ? format(t.gleif.copy, { date: status.content_date.slice(0, 10) })
      : t.gleif.unavailable;
  return (
    <Typography variant="body2" color="text.secondary">
      {t.gleif.status} {text}
    </Typography>
  );
}
