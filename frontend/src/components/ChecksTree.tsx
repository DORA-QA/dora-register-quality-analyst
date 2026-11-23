// SPDX-License-Identifier: EUPL-1.2
import Box from '@mui/material/Box';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import Typography from '@mui/material/Typography';
import { useState } from 'react';

import type { CheckStatus, ImportResponse } from '../api/imports';
import { useI18n } from '../i18n/context';
import { palette, WARNING_COLOR } from '../theme';

const STATUS_COLOR: Record<CheckStatus, string> = {
  PASSED: palette.pass,
  WARNING: WARNING_COLOR,
  FAILED: palette.fail,
  SKIPPED: palette.inkSoft,
  NOT_EVALUATED: WARNING_COLOR,
};

const STATUS_GLYPH: Record<CheckStatus, string> = {
  PASSED: '✓',
  WARNING: '⚠',
  FAILED: '✗',
  SKIPPED: '–',
  NOT_EVALUATED: '?',
};

/**
 * File > category > check, each with its result, like a control sheet.
 * The findings themselves are listed, with filters, by the findings explorer below.
 */
export function ChecksTree({ result }: { result: ImportResponse }) {
  const { t } = useI18n();
  const labels = t.result;
  const [onlyFailed, setOnlyFailed] = useState(false);

  const visible = (status: CheckStatus) =>
    status !== 'SKIPPED' &&
    (!onlyFailed || status === 'FAILED' || status === 'WARNING' || status === 'NOT_EVALUATED');
  const categories = result.categories
    .map((category) => ({
      ...category,
      checks: result.checks.filter(
        (check) => check.category === category.key && visible(check.status),
      ),
    }))
    .filter((category) => category.checks.length > 0);

  return (
    <Box>
      <FormControlLabel
        control={
          <Switch checked={onlyFailed} onChange={(event) => setOnlyFailed(event.target.checked)} />
        }
        label={labels.onlyFailed}
      />
      <Box
        sx={{
          bgcolor: 'background.paper',
          border: 1,
          borderColor: 'divider',
          p: { xs: 1.5, sm: 2.5 },
        }}
      >
        <Typography sx={{ fontWeight: 600, overflowWrap: 'anywhere' }}>
          {result.file_name}
        </Typography>
        {categories.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {labels.allPassed}
          </Typography>
        )}
        <Box component="ul" sx={{ listStyle: 'none', m: 0, pl: 2, mt: 1 }}>
          {categories.map((category) => (
            <Box component="li" key={category.key} sx={{ mt: 1.5 }}>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {category.name}
              </Typography>
              <Box
                component="ul"
                sx={{ listStyle: 'none', m: 0, pl: 2, borderLeft: 1, borderColor: 'divider' }}
              >
                {category.checks.map((check) => (
                  <Box component="li" key={check.id} sx={{ py: 0.5 }}>
                    <Typography variant="body2" sx={{ display: 'flex', gap: 1 }}>
                      <Box
                        component="span"
                        aria-hidden="true"
                        sx={{ color: STATUS_COLOR[check.status], fontWeight: 700, width: '1.25em' }}
                      >
                        {STATUS_GLYPH[check.status]}
                      </Box>
                      <Box component="span">
                        {check.name}
                        <Box component="span" sx={visuallyHidden}>
                          {t.app.colon}
                          {labels.checkStatus[check.status]}
                        </Box>
                      </Box>
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          ))}
        </Box>
      </Box>
    </Box>
  );
}

const visuallyHidden = {
  position: 'absolute',
  width: 1,
  height: 1,
  overflow: 'hidden',
  clip: 'rect(0 0 0 0)',
  whiteSpace: 'nowrap',
} as const;
