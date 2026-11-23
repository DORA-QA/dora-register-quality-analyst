// SPDX-License-Identifier: EUPL-1.2
import Accordion from '@mui/material/Accordion';
import AccordionDetails from '@mui/material/AccordionDetails';
import AccordionSummary from '@mui/material/AccordionSummary';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import type {
  ConcentrationBreakdown,
  ConcentrationIndicators,
  ImportResponse,
} from '../api/imports';
import { format, useI18n } from '../i18n/context';

const TOP = 5;

function percent(share: number): string {
  return `${Math.round(share * 1000) / 10} %`;
}

function Breakdown({ title, breakdown }: { title: string; breakdown: ConcentrationBreakdown }) {
  const { t } = useI18n();
  if (breakdown.items.length === 0) return null;
  return (
    <Box>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {title}
      </Typography>
      <Box component="ul" sx={{ mt: 0.5, mb: 0, pl: 2.5 }}>
        {breakdown.items.slice(0, TOP).map((item) => (
          <Typography component="li" variant="body2" key={item.key ?? '-'}>
            {item.label ?? item.key ?? t.concentration.unknown} · {percent(item.share)}
          </Typography>
        ))}
      </Box>
    </Box>
  );
}

/**
 * Concentration indicators (CL-43, Sprint 4, lot 2). Reading aids only: they never produce a
 * finding nor change a score. Folded by default.
 */
export function ConcentrationPanel({ result }: { result: ImportResponse }) {
  const { t, number } = useI18n();
  const labels = t.concentration;
  const state = result.concentration_state;
  const data: ConcentrationIndicators | null | undefined = result.concentration;
  if (!state) return null;

  return (
    <Accordion
      disableGutters
      elevation={0}
      slotProps={{ transition: { unmountOnExit: true } }}
      sx={{ mt: 3, border: 1, borderColor: 'divider', '&::before': { display: 'none' } }}
    >
      <AccordionSummary aria-controls="concentration-content" id="concentration-header">
        <Box>
          <Typography component="h2" sx={{ fontSize: '1.125rem', fontWeight: 600 }}>
            {labels.title}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {labels.subtitle}
          </Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails id="concentration-content">
        {state !== 'EVALUATED' || !data ? (
          <Typography variant="body2">
            {state === 'INSUFFICIENT_DATA' ? labels.insufficient : labels.notApplicable}
          </Typography>
        ) : (
          <>
            <Typography variant="body2">
              {format(labels.summary, {
                providers: number(data.providers_count),
                rows: number(data.rows),
                hhi: number(Math.round(data.hhi)),
              })}
            </Typography>
            <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 1.5 }}>
              {labels.hhiHelp}
            </Typography>

            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {labels.mainProviders}
            </Typography>
            <Box component="ul" sx={{ mt: 0.5, mb: 1.5, pl: 2.5 }}>
              {data.providers.slice(0, TOP).map((provider) => (
                <Typography
                  component="li"
                  variant="body2"
                  key={provider.code ?? provider.name ?? '-'}
                >
                  {provider.name ?? provider.code ?? labels.unknown} · {percent(provider.share)}
                  {provider.critical_functions > 0 &&
                    ` · ${format(labels.criticalFunctions, {
                      count: number(provider.critical_functions),
                    })}`}
                </Typography>
              ))}
            </Box>

            <Typography variant="body2" sx={{ mb: 1.5 }}>
              {data.single_provider_critical_functions.length === 0
                ? labels.noSingleProvider
                : format(labels.singleProvider, {
                    count: number(
                      data.single_provider_critical_functions.length +
                        data.single_provider_not_shown,
                    ),
                    list: data.single_provider_critical_functions
                      .slice(0, TOP)
                      .map((item) => `${item.function} (${item.provider ?? labels.unknown})`)
                      .join(', '),
                  })}
            </Typography>

            <Box
              sx={{
                display: 'grid',
                gap: 2,
                gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' },
              }}
            >
              <Breakdown title={labels.byServiceType} breakdown={data.by_service_type} />
              <Breakdown title={labels.byHeadquarters} breakdown={data.by_headquarters_country} />
              <Breakdown title={labels.byProvision} breakdown={data.by_provision_country} />
            </Box>
          </>
        )}
      </AccordionDetails>
    </Accordion>
  );
}
