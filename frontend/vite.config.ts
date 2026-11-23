// SPDX-License-Identifier: EUPL-1.2
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

import pkg from './package.json';

export default defineConfig({
  plugins: [react()],
  // One version for the whole product: the one of package.json (CL-41).
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  server: { host: '0.0.0.0', port: 3000 },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
