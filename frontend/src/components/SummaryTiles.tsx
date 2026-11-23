// SPDX-License-Identifier: EUPL-1.2
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import type { ImportSummary } from '../api/imports';
import { useI18n } from '../i18n/context';
import { palette, WARNING_COLOR } from '../theme';

function Tile({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <Box
      sx={{
        bgcolor: 'background.paper',
        border: 1,
        borderColor: 'divider',
        borderTop: 4,
        borderTopColor: color ?? 'divider',
        px: 2,
        py: 1.5,
      }}
    >
      <Typography sx={{ fontSize: '1.75rem', fontWeight: 600, color: color ?? 'text.primary' }}>
        {value}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}

/** Counts of the checks. The scores are in the score panel (CL-22). */
export function SummaryTiles({ summary }: { summary: ImportSummary }) {
  const { t, number } = useI18n();
  const labels = t.result;

  return (
    <Box sx={{ mt: 3 }}>
      <Box
        sx={{
          display: 'grid',
          gap: 1.5,
          gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(3, 1fr)' },
        }}
      >
        <Tile label={labels.tiles.performed} value={number(summary.checks_performed)} />
        <Tile label={labels.tiles.rows} value={number(summary.rows_analysed)} />
        <Tile label={labels.tiles.failed} value={number(summary.failed)} color={palette.fail} />
        <Tile
          label={labels.tiles.warnings}
          value={number(summary.warnings)}
          color={WARNING_COLOR}
        />
        <Tile label={labels.tiles.passed} value={number(summary.passed)} color={palette.pass} />
      </Box>
    </Box>
  );
}
