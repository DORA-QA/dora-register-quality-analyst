// SPDX-License-Identifier: EUPL-1.2
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import { useI18n } from '../i18n/context';

/**
 * Warning shown on every page of the demo build (branch demo/portable).
 *
 * It cannot be closed or switched off: this build must never be mistaken for the product.
 */
export function DemoBanner() {
  const { t } = useI18n();

  return (
    <Box
      component="aside"
      aria-label={t.demo.title}
      data-testid="demo-banner"
      sx={{
        position: 'sticky',
        top: 0,
        zIndex: (theme) => theme.zIndex.appBar + 1,
        px: 2,
        py: 1.25,
        textAlign: 'center',
        color: '#FFFFFF',
        // Diagonal stripes: impossible to confuse with a normal notice, even on a screenshot.
        backgroundColor: '#B4232C',
        backgroundImage:
          'repeating-linear-gradient(135deg, rgba(0,0,0,0.12) 0 14px, transparent 14px 28px)',
        borderBottom: '3px solid #152238',
      }}
    >
      <Typography component="p" sx={{ fontWeight: 700, letterSpacing: '0.04em' }}>
        ⚠ {t.demo.title} ⚠
      </Typography>
      <Typography component="p" variant="body2" sx={{ mt: 0.25 }}>
        {t.demo.body}
      </Typography>
    </Box>
  );
}
