// SPDX-License-Identifier: EUPL-1.2
import Accordion from '@mui/material/Accordion';
import AccordionDetails from '@mui/material/AccordionDetails';
import AccordionSummary from '@mui/material/AccordionSummary';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Collapse from '@mui/material/Collapse';
import Typography from '@mui/material/Typography';

import type { ImportMessage, Occurrence, Severity } from '../api/imports';
import { format, useI18n } from '../i18n/context';
import { useState } from 'react';

import { downloadCsv, fetchAllOccurrences, occurrencesCsv } from '../lib/occurrencesCsv';
import { palette } from '../theme';

const SEVERITY_COLOR: Record<Severity, string> = {
  BLOCKER: palette.fail,
  MAJOR: '#B4530A',
  MINOR: palette.pending,
  INFO: palette.inkSoft,
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Box sx={{ mt: 1.5 }}>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {label}
      </Typography>
      <Typography variant="body2" component="div">
        {children}
      </Typography>
    </Box>
  );
}

/** Everything below « Where » stays folded until the reader asks for it (PO, #179). */
function TechnicalDetails({ message, importId }: { message: ImportMessage; importId?: string }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [all, setAll] = useState<Occurrence[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const shownOccurrences = all ?? message.occurrences ?? [];
  const total = message.occurrences_total ?? 0;
  const available = message.occurrences_available ?? 0;
  // More occurrences are kept in memory than the answer carries: they can be read (#183).
  const canLoad =
    importId !== undefined &&
    message.index !== null &&
    message.index !== undefined &&
    available > (message.occurrences?.length ?? 0);

  const load = async (): Promise<Occurrence[] | null> => {
    if (all) return all;
    if (!canLoad) return null;
    setBusy(true);
    setFailed(false);
    try {
      const found = await fetchAllOccurrences(importId, message.index as number);
      setAll(found);
      return found;
    } catch {
      setFailed(true);
      return null;
    } finally {
      setBusy(false);
    }
  };

  const exportCsv = async () => {
    const found = (await load()) ?? message.occurrences ?? [];
    downloadCsv(
      `${message.code}-occurrences.csv`,
      occurrencesCsv(message.code, found, t.finding.csv),
    );
  };
  const hasOccurrences = (message.occurrences?.length ?? 0) > 0;
  if (!hasOccurrences && !message.reference && message.official_codes.length === 0) {
    return null;
  }
  return (
    <Box sx={{ mt: 1.5 }}>
      <Button
        size="small"
        variant="text"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        sx={{ px: 0, textTransform: 'none' }}
      >
        {open ? '▾' : '▸'} {t.finding.technicalDetails}
      </Button>
      <Collapse in={open} unmountOnExit>
        <Box>
          {shownOccurrences.length > 0 && (
            <Field label={t.finding.occurrences}>
              <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
                {shownOccurrences.map((place, position) => (
                  <li key={position}>
                    {[
                      place.table,
                      place.row !== null && format(t.finding.row, { row: place.row }),
                      place.column,
                      place.value !== null && `«\u00a0${place.value}\u00a0»`,
                      place.target_table &&
                        format(t.finding.expectedIn, {
                          target: [place.target_table, place.target_column]
                            .filter(Boolean)
                            .join(' · '),
                        }),
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                  </li>
                ))}
              </Box>
              {total > shownOccurrences.length &&
                format(t.finding.moreOccurrences, { shown: shownOccurrences.length, total })}
              <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                {canLoad && !all && (
                  <Button size="small" variant="outlined" disabled={busy} onClick={load}>
                    {format(t.finding.showAll, { total: available })}
                  </Button>
                )}
                <Button size="small" variant="outlined" disabled={busy} onClick={exportCsv}>
                  {t.finding.exportCsv}
                </Button>
              </Box>
              {failed && (
                <Typography variant="body2" role="alert" sx={{ mt: 1 }}>
                  {t.finding.loadFailed}
                </Typography>
              )}
            </Field>
          )}
          {message.reference && (
            <Field label={t.finding.reference[message.reference.type]}>
              {message.reference.text}
              {!message.reference.verified && ` ${t.finding.toConfirm}`}
            </Field>
          )}
          {message.official_codes.length > 0 && (
            <Field label={t.finding.officialCodes}>{message.official_codes.join(', ')}</Field>
          )}
        </Box>
      </Collapse>
    </Box>
  );
}

/** Findings of the import. Each one unfolds to its explanation, source and fix. */
export function MessageList({
  messages,
  importId,
}: {
  messages: ImportMessage[];
  /** Import the findings come from, to read all their occurrences (#183). */
  importId?: string;
}) {
  const { t } = useI18n();

  return (
    <Box>
      {messages.map((message, index) => (
        <Accordion
          key={`${message.code}-${index}`}
          disableGutters
          elevation={0}
          square
          sx={{
            border: 1,
            borderColor: 'divider',
            borderLeft: 4,
            borderLeftColor: SEVERITY_COLOR[message.severity],
            '&:not(:first-of-type)': { borderTop: 0 },
            '&::before': { display: 'none' },
          }}
        >
          <AccordionSummary
            expandIcon={<span aria-hidden="true">▾</span>}
            sx={{ '& .MuiAccordionSummary-content': { my: 1.25, display: 'block' } }}
          >
            <Typography
              variant="body2"
              sx={{ color: SEVERITY_COLOR[message.severity], fontWeight: 600 }}
            >
              {t.finding.severity[message.severity]} · {message.code}
              {message.eba_severity === 'warning' && ` · ${t.finding.ebaWarning}`}
              {message.severity_status === 'PROVISIONAL' && ` · ${t.finding.provisional}`}
              {message.severity_status === 'PO_VALIDATED' && ` · ${t.finding.poValidated}`}
              {message.origin && ` · ${t.finding.origin[message.origin]}`}
            </Typography>
            <Typography>{message.message}</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ pt: 0, pb: 2 }}>
            {message.explanation && <Field label={t.finding.why}>{message.explanation}</Field>}
            {message.recommendation && (
              <Field label={t.finding.what}>{message.recommendation}</Field>
            )}
            {message.expert_advice && (
              <Field label={t.finding.advice}>{message.expert_advice}</Field>
            )}
            {message.details && (
              <Field label={t.finding.where}>
                <Box component="pre" sx={{ m: 0, whiteSpace: 'pre-wrap', font: 'inherit' }}>
                  {message.details}
                </Box>
              </Field>
            )}
            <TechnicalDetails message={message} importId={importId} />
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
}
