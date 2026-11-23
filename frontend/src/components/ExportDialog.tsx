// SPDX-License-Identifier: EUPL-1.2
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControlLabel from '@mui/material/FormControlLabel';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import Typography from '@mui/material/Typography';
import { useState } from 'react';

import { exportUrl, type ExportOptions } from '../api/imports';
import { format, useI18n } from '../i18n/context';

/**
 * Export of the findings shown (Sprint 4, lot 3): CSV or JSON Lines, values included unless the
 * user leaves them out, after a confidentiality warning (§16).
 */
export function ExportDialog({
  importId,
  findings,
  table,
  row,
  column,
}: {
  importId: string;
  findings: number[];
  table?: string;
  row?: number | null;
  column?: string;
}) {
  const { t, language } = useI18n();
  const labels = t.exportDialog;
  const [open, setOpen] = useState(false);
  const [fileFormat, setFileFormat] = useState<ExportOptions['format']>('csv');
  const [withoutValues, setWithoutValues] = useState(false);

  const download = () => {
    const link = document.createElement('a');
    link.href = exportUrl(importId, {
      format: fileFormat,
      language,
      findings,
      table,
      row,
      column,
      values: !withoutValues,
    });
    link.rel = 'noopener';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setOpen(false);
  };

  return (
    <>
      <Button
        size="small"
        variant="outlined"
        disabled={findings.length === 0}
        onClick={() => setOpen(true)}
      >
        {labels.open}
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} aria-labelledby="export-title">
        <DialogTitle id="export-title">{labels.title}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            {format(labels.scope, { count: findings.length })}
          </Typography>
          <Typography variant="body2" role="note" sx={{ mb: 2, fontWeight: 600 }}>
            {labels.warning}
          </Typography>
          <RadioGroup
            row
            aria-label={labels.format}
            value={fileFormat}
            onChange={(event) => setFileFormat(event.target.value as ExportOptions['format'])}
          >
            <FormControlLabel value="csv" control={<Radio />} label={labels.csv} />
            <FormControlLabel value="jsonl" control={<Radio />} label={labels.jsonl} />
          </RadioGroup>
          <FormControlLabel
            control={
              <Checkbox
                checked={withoutValues}
                onChange={(event) => setWithoutValues(event.target.checked)}
              />
            }
            label={labels.withoutValues}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>{labels.cancel}</Button>
          <Button variant="contained" onClick={download}>
            {labels.download}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
