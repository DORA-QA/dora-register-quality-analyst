// SPDX-License-Identifier: EUPL-1.2
import { useEffect, useMemo, useState, type ReactNode } from 'react';

import {
  DICTIONARIES,
  format,
  I18nContext,
  initialLanguage,
  rememberLanguage,
  type I18n,
  type Language,
} from './context';

/** Gives the current language and its texts to the whole interface. */
export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(initialLanguage);

  useEffect(() => {
    document.documentElement.lang = language;
    rememberLanguage(language);
  }, [language]);

  const value = useMemo<I18n>(() => {
    const rules = new Intl.PluralRules(language);
    const number = (count: number) => count.toLocaleString(language);
    return {
      language,
      setLanguage,
      t: DICTIONARIES[language],
      number,
      plural: (count, forms) =>
        format(rules.select(count) === 'one' ? forms.one : forms.other, { count: number(count) }),
    };
  }, [language]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
