// SPDX-License-Identifier: EUPL-1.2
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import LinearProgress from '@mui/material/LinearProgress';
import Typography from '@mui/material/Typography';
import { useRef, useState, type DragEvent } from 'react';

import { format, useI18n } from '../i18n/context';
import { palette } from '../theme';

interface UploadPanelProps {
  /** Name of the file being analysed, if any. */
  runningFileName: string | null;
  onFile: (file: File) => void;
}

/** Where the user deposits a register: drop it or pick it. */
export function UploadPanel({ runningFileName, onFile }: UploadPanelProps) {
  const { t } = useI18n();
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const busy = runningFileName !== null;

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file && !busy) onFile(file);
  };

  return (
    <Box
      component="section"
      aria-label={t.upload.section}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      sx={{
        bgcolor: dragging ? '#E7EEF6' : 'background.paper',
        border: 1,
        borderStyle: 'dashed',
        borderColor: dragging ? palette.register : 'divider',
        px: { xs: 2.5, sm: 4 },
        py: { xs: 3, sm: 4 },
      }}
    >
      <Typography sx={{ fontSize: '1.25rem', fontWeight: 500 }}>{t.upload.title}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: '65ch' }}>
        {t.upload.help}
      </Typography>

      <input
        ref={input}
        type="file"
        hidden
        accept=".zip,.xml"
        aria-label={t.upload.fileLabel}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = '';
        }}
      />
      <Button
        variant="contained"
        disableElevation
        disabled={busy}
        onClick={() => input.current?.click()}
        sx={{ mt: 2 }}
      >
        {t.upload.choose}
      </Button>

      {busy && (
        <Box sx={{ mt: 2.5 }} role="status">
          <Typography sx={{ fontWeight: 600 }}>{t.result.loading.title}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {format(t.upload.analysing, { name: runningFileName })} · {t.result.loading.help}
          </Typography>
          <LinearProgress />
        </Box>
      )}
    </Box>
  );
}
