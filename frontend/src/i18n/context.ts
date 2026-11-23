// SPDX-License-Identifier: EUPL-1.2
import { createContext, useContext } from 'react';

import { en, type Dictionary } from './en';
import { fr } from './fr';

/** Languages of the interface. The first one is the fallback. */
export const LANGUAGES = ['en', 'fr'] as const;
export type Language = (typeof LANGUAGES)[number];

export const DICTIONARIES: Record<Language, Dictionary> = { en, fr };
/** Each language is named in its own language, so that anyone can find theirs. */
export const LANGUAGE_NAMES: Record<Language, string> = { en: 'English', fr: 'Français' };

const STORAGE_KEY = 'roi.language';

export function isLanguage(value: unknown): value is Language {
  return LANGUAGES.includes(value as Language);
}

/** Language to start with: the one chosen before, else the browser's, else English. */
export function initialLanguage(): Language {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (isLanguage(stored)) return stored;
  } catch {
    // Storage may be unavailable: the choice is simply not remembered.
  }
  const browser = navigator.language.slice(0, 2).toLowerCase();
  return isLanguage(browser) ? browser : LANGUAGES[0];
}

/** Remembers the choice in the browser. It is a display preference, not register data. */
export function rememberLanguage(language: Language): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Ignored: see initialLanguage.
  }
}

/** Replaces the `{placeholders}` of a text. */
export function format(text: string, values: Record<string, string | number> = {}): string {
  return text.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in values ? String(values[name]) : match,
  );
}

export interface I18n {
  language: Language;
  setLanguage: (language: Language) => void;
  /** Texts of the current language. */
  t: Dictionary;
  /** Formats a number the way the current language writes it. */
  number: (value: number) => string;
  /** Picks the singular or plural form and inserts the formatted count. */
  plural: (value: number, forms: { one: string; other: string }) => string;
}

export const I18nContext = createContext<I18n | null>(null);

export function useI18n(): I18n {
  const context = useContext(I18nContext);
  if (context === null) throw new Error('useI18n must be used inside I18nProvider');
  return context;
}
