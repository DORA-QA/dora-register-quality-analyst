// SPDX-License-Identifier: EUPL-1.2
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import { useState } from 'react';

import { fetchAbout, type AboutInfo, type AboutSource } from '../api/about';
import { format, useI18n } from '../i18n/context';

type State = { state: 'loading' } | { state: 'ok'; about: AboutInfo } | { state: 'error' };

/**
 * « About the engine » (Sprint 4, §22 and §23): version, taxonomy, catalogue and its fingerprint,
 * sources of the checks, score warning, and empty places for the legal notice and the licence.
 * Everything is read from the local API: nothing is fetched from the Internet.
 */
export function AboutDialog() {
  const { t } = useI18n();
  const labels = t.about;
  const [open, setOpen] = useState(false);
  const [info, setInfo] = useState<State>({ state: 'loading' });

  const show = () => {
    setOpen(true);
    setInfo({ state: 'loading' });
    fetchAbout()
      .then((about) => setInfo({ state: 'ok', about }))
      .catch(() => setInfo({ state: 'error' }));
  };

  const sourceName = (source: AboutSource) =>
    labels.sources[source.id as keyof typeof labels.sources] ?? source.title ?? source.id;

  return (
    <>
      <Button size="small" variant="text" onClick={show} sx={{ px: 0 }}>
        {labels.button}
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} aria-labelledby="about-title">
        <DialogTitle id="about-title">{labels.title}</DialogTitle>
        <DialogContent>
          {info.state === 'loading' && <Typography>{labels.loading}</Typography>}
          {info.state === 'error' && <Typography>{labels.error}</Typography>}
          {info.state === 'ok' && (
            <>
              <Typography variant="h3" sx={{ fontSize: '1rem', mb: 1 }}>
                {labels.engine}
              </Typography>
              <Typography variant="body2">
                {format(labels.version, { version: info.about.version })}
              </Typography>
              <Typography variant="body2">
                {format(labels.taxonomy, { version: info.about.taxonomy_version })}
              </Typography>
              <Typography variant="body2">
                {format(labels.catalog, {
                  count: info.about.catalog_codes,
                  fingerprint: info.about.catalog_fingerprint,
                })}
              </Typography>

              <Typography variant="h3" sx={{ fontSize: '1rem', mt: 2, mb: 1 }}>
                {labels.sourcesTitle}
              </Typography>
              <ul style={{ margin: 0, paddingLeft: '1.2rem' }}>
                {info.about.sources.map((source) => (
                  <li key={source.id}>
                    <Typography variant="body2" component="span">
                      {source.url ? (
                        <Link href={source.url} target="_blank" rel="noopener noreferrer">
                          {sourceName(source)}
                        </Link>
                      ) : (
                        sourceName(source)
                      )}
                      {source.published && ` · ${source.published}`}
                      {source.sha256 && ` · SHA-256 ${source.sha256.slice(0, 12)}`}
                    </Typography>
                  </li>
                ))}
              </ul>

              <Typography variant="h3" sx={{ fontSize: '1rem', mt: 2, mb: 1 }}>
                {labels.scoresTitle}
              </Typography>
              <Typography variant="body2">{t.scores.warning}</Typography>

              <Typography variant="h3" sx={{ fontSize: '1rem', mt: 2, mb: 1 }}>
                {labels.legalTitle}
              </Typography>
              <Typography variant="body2">{t.disclaimer.body}</Typography>
              <Typography variant="h3" sx={{ fontSize: '1rem', mt: 2, mb: 1 }}>
                {labels.licenceTitle}
              </Typography>
              <Typography variant="body2">{info.about.licence ?? labels.notYet}</Typography>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>{labels.close}</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
