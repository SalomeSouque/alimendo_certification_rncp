import { defineConfig, loadEnv } from 'vite'
import { configDefaults } from 'vitest/config'
import react from '@vitejs/plugin-react'

/**
 * Link previews need absolute URLs (og:image). The site and its API share the same
 * domain in production (VITE_API_URL = https://<domain>/api), so the site URL is the
 * origin of VITE_API_URL: the domain stays out of the repository.
 */
function siteUrl(mode) {
  const { VITE_API_URL } = { ...loadEnv(mode, process.cwd()), ...process.env };
  try {
    return new URL(VITE_API_URL).origin;
  } catch {
    return '';
  }
}

/**
 * Where the page may load things from. Anything else is blocked by the browser:
 * an injected script (XSS) cannot run nor send data to another site.
 */
function contentSecurityPolicy(mode) {
  const { VITE_API_URL } = { ...loadEnv(mode, process.cwd()), ...process.env };
  let api = '';
  try {
    api = new URL(VITE_API_URL).origin;
  } catch {
    // no API URL: same origin only
  }
  return [
    "default-src 'self'",
    "script-src 'self'",
    // 'unsafe-inline': React style={…} attributes (home page zoom, positions).
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    // data:/blob: photo preview; Open Food Facts product pictures.
    "img-src 'self' data: blob: https://*.openfoodfacts.org",
    `connect-src 'self' ${api}`.trim(),
    "media-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ');
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    {
      name: 'site-url-in-html',
      transformIndexHtml: (html) => html.replaceAll('%SITE_URL%', siteUrl(mode)),
    },
    {
      // Content-Security-Policy of the production build (not in dev: Vite's hot reload
      // uses inline scripts and a websocket). It lives in the page rather than in
      // nginx.conf because the API address (connect-src) is only known at build time.
      name: 'content-security-policy',
      apply: 'build',
      transformIndexHtml: (html) => html.replace(
        '<meta charset="UTF-8" />',
        `<meta charset="UTF-8" />\n    <meta http-equiv="Content-Security-Policy" content="${contentSecurityPolicy(mode)}" />`,
      ),
    },
  ],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    // e2e/ is run by Playwright in a real browser (npm run test:e2e), not by Vitest.
    exclude: [...configDefaults.exclude, 'e2e/**'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{js,jsx}'],
      exclude: ['src/**/*.test.{js,jsx}', 'src/test/**', 'src/main.jsx'],
      reporter: ['text', 'html'],
    },
  },
}))
