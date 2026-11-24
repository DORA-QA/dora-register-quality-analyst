// SPDX-License-Identifier: EUPL-1.2
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Box from '@mui/material/Box';
import LinearProgress from '@mui/material/LinearProgress';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import { useState } from 'react';

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
  if (status.state === 'UPDATING') return null;
  // Offline version (decision A9): say plainly that the GLEIF checks are not part of it.
  const text =
    status.state === 'DISABLED'
      ? t.gleif.offline
      : status.state === 'READY' && status.content_date
        ? format(t.gleif.copy, { date: status.content_date.slice(0, 10) })
        : t.gleif.unavailable;
  return (
    <Typography variant="body2" color="text.secondary">
      {t.gleif.status} {text}
    </Typography>
  );
}

/**
 * Shown after the waiting screen when the online update failed: what went wrong, what the
 * analysis will do without a fresh copy, and what to try next. The user may close it.
 */
export function GleifFailure({ status }: { status: GleifStatus }) {
  const { t } = useI18n();
  const [closed, setClosed] = useState(false);
  const code = status.last_error;
  if (closed || !code || (status.state !== 'READY' && status.state !== 'UNAVAILABLE')) return null;

  const reasons: Record<string, string> = t.gleif.failed.reasons;
  const reason = reasons[code] ?? t.gleif.failed.reasons.internal;
  const kept = status.state === 'READY' && status.content_date;
  return (
    <Alert
      severity={kept ? 'warning' : 'error'}
      variant="outlined"
      onClose={() => setClosed(true)}
      sx={{ mb: 3 }}
    >
      <AlertTitle>{t.gleif.failed.title}</AlertTitle>
      <Typography variant="body2" sx={{ mb: 1 }}>
        {reason}
      </Typography>
      <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
        {kept
          ? format(t.gleif.failed.kept, { date: (status.content_date ?? '').slice(0, 10) })
          : t.gleif.failed.none}
      </Typography>
      {code === 'network' && (
        <Typography variant="body2" sx={{ mb: 1 }}>
          {t.gleif.failed.network}
        </Typography>
      )}
      <Typography variant="body2">{t.gleif.failed.retry}</Typography>
      <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 1 }}>
        {format(t.gleif.failed.code, { code })}
      </Typography>
    </Alert>
  );
}
