// SPDX-License-Identifier: EUPL-1.2
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import type { ImportOverview } from '../api/imports';
import { useI18n } from '../i18n/context';
import { palette, WARNING_COLOR } from '../theme';

const VERDICT_COLOR: Record<ImportOverview['verdict'], string> = {
  BLOCKED: palette.fail,
  CORRECTIONS: WARNING_COLOR,
  GOOD: palette.pass,
};

/**
 * « En résumé » (CL-37): the overview written by the engine from its own figures, without AI.
 * Every sentence comes from the API, in the language of the answer.
 */
export function OverviewPanel({ overview }: { overview: ImportOverview }) {
  const { t } = useI18n();
  const labels = t.overview;

  return (
    <Box
      component="section"
      aria-label={labels.title}
      sx={{
        mt: 3,
        bgcolor: 'background.paper',
        border: 1,
        borderColor: 'divider',
        px: { xs: 2.5, sm: 4 },
        py: { xs: 2, sm: 2.5 },
      }}
    >
      <Typography component="h2" sx={{ fontSize: '1.125rem', fontWeight: 600 }}>
        {labels.title}
      </Typography>
      <Typography sx={{ mt: 1, fontWeight: 600, color: VERDICT_COLOR[overview.verdict] }}>
        {overview.headline}
      </Typography>
      <Typography variant="body2" sx={{ mt: 1 }}>
        {overview.figures}
      </Typography>
      {overview.tables && (
        <Typography variant="body2" sx={{ mt: 1 }}>
          {overview.tables}
        </Typography>
      )}
      {overview.gleif && (
        <Typography variant="body2" sx={{ mt: 1 }}>
          {overview.gleif}
        </Typography>
      )}
      {overview.priorities.length > 0 && (
        <>
          <Typography variant="body2" sx={{ mt: 1.5, fontWeight: 600 }}>
            {labels.priorities}
          </Typography>
          <Box component="ol" sx={{ mt: 0.5, mb: 0, pl: 3 }}>
            {overview.priorities.map((priority, position) => (
              <Box component="li" key={`${priority.code}-${position}`} sx={{ mb: 0.75 }}>
                <Typography variant="body2">
                  <Box component="span" sx={{ fontWeight: 600 }}>
                    {t.finding.severity[priority.severity]} · {priority.code}
                  </Box>{' '}
                  {priority.finding}
                </Typography>
                {priority.action && (
                  <Typography variant="body2" color="text.secondary">
                    {priority.action}
                  </Typography>
                )}
              </Box>
            ))}
          </Box>
        </>
      )}
      {overview.profiles && (
        <Typography variant="body2" sx={{ mt: 1 }}>
          {overview.profiles}
        </Typography>
      )}
      <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 1.5, mb: 0 }}>
        {overview.note}
      </Typography>
    </Box>
  );
}
