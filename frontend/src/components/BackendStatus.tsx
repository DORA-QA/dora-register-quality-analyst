// SPDX-License-Identifier: EUPL-1.2
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';

import { API_URL } from '../config';
import type { BackendHealth } from '../hooks/useBackendHealth';
import { format, useI18n } from '../i18n/context';
import { palette } from '../theme';

interface BackendStatusProps {
  health: BackendHealth;
  onCheckAgain: () => void;
}

const COLOR = {
  checking: palette.pending,
  ok: palette.pass,
  unreachable: palette.fail,
} as const;

/** One line telling whether the API answers, with what to do when it does not. */
export function BackendStatus({ health, onCheckAgain }: BackendStatusProps) {
  const { t } = useI18n();
  const healthUrl = `${API_URL}/health`;

  return (
    <Box aria-live="polite">
      <Typography variant="body2" color="text.secondary">
        {t.backend.status}{' '}
        <Box component="span" sx={{ color: COLOR[health.state], fontWeight: 600 }}>
          {t.backend[health.state]}
        </Box>
        {health.state === 'ok' &&
          ` · ${format(t.backend.apiVersion, { version: health.version })}${
            health.taxonomy ? ` · ${format(t.backend.taxonomy, { version: health.taxonomy })}` : ''
          }`}
        {health.state === 'checking' && ` · ${format(t.backend.calling, { url: healthUrl })}`}
      </Typography>

      {health.state === 'unreachable' && (
        <Box sx={{ mt: 1 }}>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '60ch' }}>
            {format(t.backend.helpBefore, { url: healthUrl })} <code>docker compose ps</code>
            {t.backend.helpAfter}
          </Typography>
          <Button variant="outlined" size="small" onClick={onCheckAgain} sx={{ mt: 1 }}>
            {t.backend.checkAgain}
          </Button>
        </Box>
      )}
    </Box>
  );
}
