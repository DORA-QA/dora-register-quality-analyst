// SPDX-License-Identifier: EUPL-1.2
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';

import type { ImportResponse, ImportStatus } from '../api/imports';
import { format, useI18n } from '../i18n/context';
import { palette } from '../theme';
import { ChecksTree } from './ChecksTree';
import { FindingsExplorer } from './FindingsExplorer';
import { ConcentrationPanel } from './ConcentrationPanel';
import { OverviewPanel } from './OverviewPanel';
import { ScorePanel } from './ScorePanel';
import { SummaryTiles } from './SummaryTiles';

const STATUS_COLOR: Record<ImportStatus, string> = {
  SUCCESS: palette.pass,
  SUCCESS_WITH_WARNINGS: palette.pending,
  FAILED: palette.fail,
};

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <Typography component="h2" sx={{ fontSize: '1.125rem', fontWeight: 600, mt: 4, mb: 1.5 }}>
      {children}
    </Typography>
  );
}

/** Everything the user needs to judge an import: verdict, identity, tables, findings. */
export function ImportResult({
  result,
  onRestart,
}: {
  result: ImportResponse;
  onRestart: () => void;
}) {
  const { t, number, plural } = useI18n();
  const labels = t.result;
  const color = STATUS_COLOR[result.status];
  const { metadata, counts } = result;
  const identity: [string, string | null][] = [
    [labels.identity.file, result.file_name],
    [
      labels.identity.source,
      result.source_type + (metadata.channel ? ` (${metadata.channel})` : ''),
    ],
    [labels.identity.entity, metadata.entity_lei],
    [labels.identity.scope, metadata.reporting_scope],
    [labels.identity.referenceDate, metadata.reference_date],
    [labels.identity.taxonomyVersion, metadata.taxonomy_version],
    [labels.identity.currency, metadata.base_currency],
    [labels.identity.envelopeDomain, metadata.envelope_domain],
  ];
  const summary = [
    plural(result.tables_loaded, labels.counts.tables),
    plural(result.rows_loaded, labels.counts.rows),
    plural(counts.blocker, labels.counts.blockers),
    plural(counts.major, labels.counts.majors),
    plural(counts.minor, labels.counts.minors),
  ].join(' · ');

  return (
    <Box component="section" aria-label={labels.section} sx={{ mt: 4 }}>
      <Box
        sx={{
          bgcolor: 'background.paper',
          border: 1,
          borderColor: 'divider',
          borderLeft: 6,
          borderLeftColor: color,
          px: { xs: 2.5, sm: 4 },
          py: { xs: 2.5, sm: 3 },
        }}
      >
        <Typography sx={{ fontSize: { xs: '1.5rem', sm: '1.75rem' }, fontWeight: 500 }}>
          {labels.heading}{' '}
          <Box component="span" sx={{ color, fontWeight: 600 }}>
            {labels.status[result.status]}
          </Box>
        </Typography>
        <Typography sx={{ mt: 0.5 }}>{labels.summary[result.status]}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {summary}
        </Typography>
      </Box>

      {result.overview && <OverviewPanel overview={result.overview} />}

      <SummaryTiles summary={result.summary} />
      {result.scores && <ScorePanel scores={result.scores} />}
      <ConcentrationPanel result={result} />

      <SectionTitle>{labels.package}</SectionTitle>
      <Box
        component="dl"
        sx={{
          m: 0,
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'max-content 1fr' },
          columnGap: 3,
          rowGap: 0.5,
        }}
      >
        {identity
          .filter(([, value]) => value)
          .map(([label, value]) => (
            <Box key={label} sx={{ display: 'contents' }}>
              <Typography component="dt" variant="body2" color="text.secondary">
                {label}
              </Typography>
              <Typography component="dd" variant="body2" sx={{ m: 0, overflowWrap: 'anywhere' }}>
                {value}
              </Typography>
            </Box>
          ))}
      </Box>

      <SectionTitle>{labels.checks}</SectionTitle>
      <ChecksTree result={result} />

      <SectionTitle>{format(labels.findings, { count: result.messages.length })}</SectionTitle>
      <FindingsExplorer result={result} />

      <SectionTitle>{format(labels.tables, { count: result.tables.length })}</SectionTitle>
      {result.missing_rt.length > 0 && (
        <Typography variant="body2" sx={{ mb: 1.5, color: palette.fail }}>
          {format(labels.missingTemplates, { list: result.missing_rt.join(', ') })}
        </Typography>
      )}
      {result.tables.length > 0 && (
        <TableContainer sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider' }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{labels.columns.table}</TableCell>
                <TableCell>{labels.columns.file}</TableCell>
                <TableCell align="right">{labels.columns.rows}</TableCell>
                <TableCell align="right">{labels.columns.columns}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {result.tables.map((table) => (
                <TableRow key={table.code}>
                  <TableCell>{table.code}</TableCell>
                  <TableCell>{table.file}</TableCell>
                  <TableCell align="right">{number(table.rows)}</TableCell>
                  <TableCell align="right">{table.columns}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Button variant="outlined" onClick={onRestart} sx={{ mt: 4 }}>
        {labels.restart}
      </Button>
    </Box>
  );
}
