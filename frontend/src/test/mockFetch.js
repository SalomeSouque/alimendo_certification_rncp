// src/test/mockFetch.js
// Simulated fetch for integration tests: no network, responses declared per test.
import { vi } from 'vitest';

/**
 * Builds a Response-like object as returned by fetch.
 * @param {number} status
 * @param {any} [body] - serialised as JSON when provided.
 */
export function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: String(status),
    json: async () => {
      if (body === undefined) throw new SyntaxError('No JSON body');
      return body;
    },
  };
}

/**
 * Replaces global fetch with a mock answering the given responses in order.
 * A function entry is called with (url, options) and must return a response.
 * @param {...any} responses
 * @returns {import('vitest').Mock}
 */
export function mockFetch(...responses) {
  const fn = vi.fn();
  responses.forEach((r) => {
    fn.mockImplementationOnce(async (url, options) => (typeof r === 'function' ? r(url, options) : r));
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}