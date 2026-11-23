// SPDX-License-Identifier: EUPL-1.2
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Typography from '@mui/material/Typography';
import { useState } from 'react';

import type { ImportMessage, ImportResponse, RuleOrigin, Severity } from '../api/imports';
import { format, useI18n } from '../i18n/context';
import {
  filterFindings,
  hasActiveFilter,
  NO_FILTERS,
  placeValues,
  type FindingFilters,
} from '../lib/findingFilters';
import { ExportDialog } from './ExportDialog';
import { MessageList } from './MessageList';

const SEVERITIES: Severity[] = ['BLOCKER', 'MAJOR', 'MINOR', 'INFO'];
const ORIGINS: RuleOrigin[] = ['OFFICIAL', 'TECHNICAL', 'PO_VALIDATED', 'DATA_QUALITY'];
const STATUSES: ImportMessage['severity_status'][] = ['CONFIRMED', 'PROVISIONAL', 'PO_VALIDATED'];

/** Views of the findings (CL-22): all, official rules and technical checks, expert advice. */
type View = 'ALL' | 'REGULATORY' | 'EXPERT';

/** All findings in one list, filterable by severity, category, check, table, row and column. */
export function FindingsExplorer({ result }: { result: ImportResponse }) {
  const { t } = useI18n();
  const labels = t.explorer;
  const [filters, setFilters] = useState<FindingFilters>(NO_FILTERS);

  const set = (key: keyof FindingFilters) => (event: { target: { value: string } }) =>
    setFilters((current) => ({ ...current, [key]: event.target.value }));

  const [view, setView] = useState<View>('ALL');
  const inView = (profile: string | null | undefined) =>
    view === 'ALL' || (view === 'EXPERT' ? profile === 'EXPERT' : profile !== 'EXPERT');
  const shown = filterFindings(result, filters).filter((message) => inView(message.profile));
  const expertCount = result.messages.filter((message) => message.profile === 'EXPERT').length;
  const select = (
    key: 'severity' | 'origin' | 'status' | 'category' | 'check' | 'table' | 'column',
    label: string,
    options: { value: string; label: string }[],
  ) => (
    <TextField
      select
      size="small"
      label={label}
      value={filters[key]}
      onChange={set(key)}
      sx={{ minWidth: 160, flex: '1 1 160px' }}
    >
      <MenuItem value="">{labels.all}</MenuItem>
      {options.map((option) => (
        <MenuItem key={option.value} value={option.value}>
          {option.label}
        </MenuItem>
      ))}
    </TextField>
  );

  return (
    <Box>
      <ToggleButtonGroup
        exclusive
        size="small"
        value={view}
        aria-label={labels.view}
        onChange={(_, value: View | null) => value && setView(value)}
        sx={{ mb: 2, flexWrap: 'wrap' }}
      >
        <ToggleButton value="ALL">{labels.viewAll}</ToggleButton>
        <ToggleButton value="REGULATORY">{labels.viewRegulatory}</ToggleButton>
        <ToggleButton value="EXPERT">{labels.viewExpert}</ToggleButton>
      </ToggleButtonGroup>
      {view === 'EXPERT' && (
        <Typography
          variant="body2"
          sx={{
            mb: 2,
            px: 2,
            py: 1,
            border: 1,
            borderColor: 'divider',
            bgcolor: 'background.paper',
          }}
        >
          {labels.expertBanner}
        </Typography>
      )}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, mb: 2 }}>
        {select(
          'severity',
          labels.severity,
          SEVERITIES.map((value) => ({ value, label: t.finding.severity[value] })),
        )}
        {select(
          'origin',
          labels.origin,
          ORIGINS.map((value) => ({ value, label: t.finding.origin[value] })),
        )}
        {select(
          'status',
          labels.status,
          STATUSES.map((value) => ({ value, label: labels.statuses[value] })),
        )}
        {select(
          'category',
          labels.category,
          result.categories.map((item) => ({ value: item.key, label: item.name })),
        )}
        {select(
          'check',
          labels.check,
          result.checks.map((item) => ({ value: item.id, label: item.name })),
        )}
        {select(
          'table',
          labels.table,
          placeValues(result.messages, 'table').map((value) => ({ value, label: value })),
        )}
        <TextField
          size="small"
          type="number"
          label={labels.row}
          value={filters.row}
          onChange={set('row')}
          slotProps={{ htmlInput: { min: 1 } }}
          sx={{ width: 110 }}
        />
        {select(
          'column',
          labels.column,
          placeValues(result.messages, 'column').map((value) => ({ value, label: value })),
        )}
        {hasActiveFilter(filters) && (
          <Button onClick={() => setFilters(NO_FILTERS)}>{labels.reset}</Button>
        )}
      </Box>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1,
          flexWrap: 'wrap',
          mb: 1,
        }}
      >
        <Typography variant="body2" color="text.secondary" role="status" sx={{ mb: 1 }}>
          {format(labels.count, { shown: shown.length, total: result.messages.length })}
          {view === 'REGULATORY' &&
            expertCount > 0 &&
            ` · ${format(labels.moreExpert, { count: expertCount })}`}
        </Typography>
        <ExportDialog
          importId={result.import_id}
          findings={shown.map((message) => message.index).filter((i): i is number => i != null)}
          table={filters.table || undefined}
          row={filters.row.trim() === '' ? null : Number(filters.row)}
          column={filters.column || undefined}
        />
      </Box>
      {shown.length === 0 ? (
        <Typography variant="body2">{labels.none}</Typography>
      ) : (
        <MessageList messages={shown} importId={result.import_id} />
      )}
    </Box>
  );
}
