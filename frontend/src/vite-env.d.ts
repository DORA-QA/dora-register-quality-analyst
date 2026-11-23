/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the backend API, as seen from the browser. */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
