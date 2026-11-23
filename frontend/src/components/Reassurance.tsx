// SPDX-License-Identifier: EUPL-1.2
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import { useI18n } from '../i18n/context';
import { palette } from '../theme';

/** What the visitor wants to know before depositing a register: where it goes (nowhere). */
export function Reassurance() {
  const { t } = useI18n();
  const { title, points } = t.result.reassure;

  return (
    <Box component="section" aria-label={title} sx={{ mt: 4 }}>
      <Typography component="h2" sx={{ fontSize: '1.125rem', fontWeight: 600, mb: 1.5 }}>
        {title}
      </Typography>
      <Box
        component="ul"
        sx={{ m: 0, p: 0, listStyle: 'none', display: 'grid', gap: 1.25, maxWidth: '70ch' }}
      >
        {points.map((point) => (
          <Typography
            component="li"
            key={point}
            variant="body2"
            sx={{ display: 'flex', gap: 1.25 }}
          >
            <Box component="span" aria-hidden="true" sx={{ color: palette.pass, fontWeight: 700 }}>
              ✓
            </Box>
            {point}
          </Typography>
        ))}
      </Box>
    </Box>
  );
}
