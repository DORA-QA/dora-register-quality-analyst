// SPDX-License-Identifier: EUPL-1.2
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Collapse from '@mui/material/Collapse';
import Typography from '@mui/material/Typography';
import { useState } from 'react';

import type { ImportScores, ProfileScore } from '../api/imports';
import { format, useI18n } from '../i18n/context';
import { palette, WARNING_COLOR } from '../theme';

const RADIUS = 26;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function scoreColor(score: number | null): string {
  if (score === null) return palette.line;
  if (score >= 90) return palette.pass;
  if (score >= 60) return WARNING_COLOR;
  return palette.fail;
}

/** Ring with the value written inside; a missing score is shown as « – », never as 0. */
function Donut({ value }: { value: number | null }) {
  const color = scoreColor(value);
  return (
    <svg width="64" height="64" viewBox="0 0 64 64" aria-hidden="true" style={{ flexShrink: 0 }}>
      <circle cx="32" cy="32" r={RADIUS} fill="none" stroke={palette.line} strokeWidth="8" />
      {value !== null && (
        <circle
          cx="32"
          cy="32"
          r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={`${(CIRCUMFERENCE * value) / 100} ${CIRCUMFERENCE}`}
          transform="rotate(-90 32 32)"
        />
      )}
      <text x="32" y="38" textAnchor="middle" fontSize="16" fontWeight="600" fill={color}>
        {value === null ? '–' : value}
      </text>
    </svg>
  );
}

function Card({
  title,
  value,
  lines,
}: {
  title: string;
  value: number | null;
  lines: (string | null)[];
}) {
  const { t } = useI18n();
  return (
    <Box
      sx={{
        bgcolor: 'background.paper',
        border: 1,
        borderColor: 'divider',
        px: 2,
        py: 1.5,
        display: 'flex',
        gap: 2,
        alignItems: 'flex-start',
      }}
    >
      <Donut value={value} />
      <Box>
        <Typography sx={{ fontWeight: 600 }}>
          {title}
          {t.app.colon}
          {value === null ? t.scores.notEvaluated : `${value}/100`}
        </Typography>
        {lines
          .filter((line): line is string => Boolean(line))
          .map((line) => (
            <Typography key={line} variant="body2" color="text.secondary">
              {line}
            </Typography>
          ))}
      </Box>
    </Box>
  );
}

/** The three scores of the engine (CL-22): regulatory, quality and confidence. */
export function ScorePanel({ scores }: { scores: ImportScores }) {
  const { t, number, plural } = useI18n();
  const labels = t.scores;
  const [open, setOpen] = useState(false);

  const describe = (score: ProfileScore): (string | null)[] => [
    format(labels.weights, {
      earned: number(score.weight_earned),
      total: number(score.weight_total),
      checks: number(score.checks_performed),
    }),
    score.not_run.length + score.not_evaluated.length > 0
      ? format(labels.notRun, { list: [...score.not_run, ...score.not_evaluated].join(', ') })
      : null,
    score.provisional_findings > 0 ? plural(score.provisional_findings, labels.provisional) : null,
  ];

  const confidence = scores.confidence;
  const confidenceLine =
    confidence.value === null
      ? format(labels.confidenceNotRun, { list: confidence.not_run.join(', ') })
      : confidence.value === 0
        ? labels.confidenceBlocked
        : labels.confidenceFull;

  return (
    <Box sx={{ mt: 2 }}>
      <Box
        sx={{
          display: 'grid',
          gap: 1.5,
          gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' },
        }}
      >
        <Card
          title={labels.regulatory}
          value={scores.regulatory.value}
          lines={[labels.regulatoryScope, ...describe(scores.regulatory)]}
        />
        <Card
          title={labels.quality}
          value={scores.quality.value}
          lines={[labels.qualityScope, ...describe(scores.quality)]}
        />
        <Card title={labels.confidence} value={confidence.value} lines={[confidenceLine]} />
      </Box>
      <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 1, mb: 0 }}>
        {labels.warning}
      </Typography>
      <Button
        size="small"
        variant="text"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        sx={{ px: 0, textTransform: 'none' }}
      >
        {open ? '▾' : '▸'} {labels.how}
      </Button>
      <Collapse in={open} unmountOnExit>
        <Box component="ol" sx={{ mt: 0, pl: 3 }}>
          {Object.values(labels.formula).map((step) => (
            <Typography component="li" variant="body2" key={step}>
              {step}
            </Typography>
          ))}
        </Box>
      </Collapse>
    </Box>
  );
}
