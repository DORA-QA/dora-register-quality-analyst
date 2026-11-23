// SPDX-License-Identifier: EUPL-1.2
import { createTheme } from '@mui/material/styles';

/** Palette of the product: a control sheet, ink on cool paper, colour only for results. */
export const palette = {
  paper: '#F2F4F6',
  sheet: '#FFFFFF',
  ink: '#152238',
  inkSoft: '#51607A',
  line: '#CBD3DC',
  register: '#1D4E89',
  pass: '#1B7F5A',
  fail: '#B4232C',
  pending: '#8A6100',
} as const;

const fontFamily = '"IBM Plex Sans", "Helvetica Neue", Arial, sans-serif';

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: palette.register },
    success: { main: palette.pass },
    error: { main: palette.fail },
    warning: { main: palette.pending },
    background: { default: palette.paper, paper: palette.sheet },
    text: { primary: palette.ink, secondary: palette.inkSoft },
    divider: palette.line,
  },
  shape: { borderRadius: 2 },
  typography: {
    fontFamily,
    h1: { fontSize: '2.25rem', fontWeight: 600, lineHeight: 1.15, letterSpacing: '-0.015em' },
    body1: { fontSize: '1rem', lineHeight: 1.5 },
    body2: { fontSize: '0.875rem', lineHeight: 1.5 },
    button: { textTransform: 'none', fontWeight: 500 },
  },
});

/** Colour of a warning: orange, distinct from the failure red and the pass green. */
export const WARNING_COLOR = '#B4530A';
