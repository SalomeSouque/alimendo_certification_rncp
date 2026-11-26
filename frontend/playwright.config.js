// playwright.config.js
// Responsive + accessibility checks in a real browser.
// Unit tests stay in Vitest (jsdom, no layout); this suite needs real CSS layout.
//
//   npm run test:e2e            run every page at the 4 reference widths
//   npx playwright show-report  open the HTML report (screenshots, axe details)

import { defineConfig } from '@playwright/test';
import { API_URL } from './e2e/support/mockApi.js';

// The front talks to a fake API origin (API_URL), answered by e2e/support/mockApi.js:
// no backend, database or Mistral key needed, and the data never changes between runs.
const PORT = 5174;

// Reference widths: 320 = WCAG 1.4.10 reflow, 360 = common Android, 390 = recent iPhone,
// 768 = tablet portrait, 1280 = laptop. (375, 412 and 430 were also checked once.)
const VIEWPORTS = [
  { name: 'mobile-320', width: 320, height: 640, mobile: true },
  { name: 'mobile-360', width: 360, height: 780, mobile: true },
  { name: 'mobile-390', width: 390, height: 844, mobile: true },
  { name: 'tablet-768', width: 768, height: 1024, mobile: true },
  { name: 'desktop-1280', width: 1280, height: 800, mobile: false },
];

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: `http://localhost:${PORT}`,
    locale: 'fr-FR',
    trace: 'retain-on-failure',
    launchOptions: {
      // Fake camera (moving test pattern) with permission granted: the barcode
      // tab opens its camera as on a phone.
      args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'],
      // Only used where Playwright cannot download its own browser.
      ...(process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {}),
    },
  },
  projects: VIEWPORTS.map(({ name, width, height, mobile }) => ({
    name,
    use: {
      browserName: 'chromium',
      viewport: { width, height },
      // isMobile: the <meta name="viewport"> is honoured, like on a real phone.
      isMobile: mobile,
      hasTouch: mobile,
      deviceScaleFactor: 1,
    },
  })),
  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    env: { VITE_API_URL: API_URL, VITE_AUTH_MOCK: 'false' },
  },
});
