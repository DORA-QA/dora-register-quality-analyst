// SPDX-License-Identifier: EUPL-1.2
/** Product name shown in the interface. */
export const APP_NAME = 'DORA QA';

/** Version shown on the home page, taken from package.json at build time (CL-41). */
export const APP_VERSION: string = __APP_VERSION__;

/** Base URL of the backend API, as seen from the browser. */
export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(
  /\/+$/,
  '',
);
