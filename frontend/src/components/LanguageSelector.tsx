// SPDX-License-Identifier: EUPL-1.2
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';

import { isLanguage, LANGUAGE_NAMES, LANGUAGES, useI18n } from '../i18n/context';

/** Lets the user choose the language of the interface and of the findings. */
export function LanguageSelector() {
  const { language, setLanguage, t } = useI18n();

  return (
    <ToggleButtonGroup
      exclusive
      size="small"
      value={language}
      aria-label={t.language.label}
      onChange={(_, value: unknown) => {
        if (isLanguage(value)) setLanguage(value);
      }}
    >
      {LANGUAGES.map((code) => (
        <ToggleButton
          key={code}
          value={code}
          lang={code}
          aria-label={LANGUAGE_NAMES[code]}
          sx={{ px: 1.5, py: 0.25, fontWeight: 600 }}
        >
          {code.toUpperCase()}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}
