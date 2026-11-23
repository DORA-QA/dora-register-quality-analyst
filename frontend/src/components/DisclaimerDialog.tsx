// SPDX-License-Identifier: EUPL-1.2
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControlLabel from '@mui/material/FormControlLabel';
import Typography from '@mui/material/Typography';
import { useState } from 'react';

import { useI18n } from '../i18n/context';
import { LanguageSelector } from './LanguageSelector';

/**
 * Disclaimer shown at every launch (decision of 23/11/2026, A7 and A8).
 *
 * Blocking (no onClose): no escape key, no click outside, nothing usable behind it until the box is ticked
 * and confirmed. The acceptance lives in memory only: nothing is written to disk or to the
 * browser storage, so the window comes back at the next launch.
 */
export function DisclaimerDialog({ onAccept }: { onAccept: () => void }) {
  const { t } = useI18n();
  const [ticked, setTicked] = useState(false);

  return (
    <Dialog open aria-labelledby="disclaimer-title" maxWidth="sm" fullWidth>
      <DialogTitle
        id="disclaimer-bar"
        sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2 }}
      >
        <span id="disclaimer-title">{t.disclaimer.title}</span>
        <LanguageSelector />
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>
          {t.disclaimer.body}
        </Typography>
        <FormControlLabel
          sx={{ mt: 2 }}
          control={<Checkbox checked={ticked} onChange={(e) => setTicked(e.target.checked)} />}
          label={t.disclaimer.accept}
        />
      </DialogContent>
      <DialogActions>
        <Button variant="contained" disabled={!ticked} onClick={onAccept}>
          {t.disclaimer.continue}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
