// src/test/viewport.js
// jsdom has no layout and no matchMedia: by default the components render their
// desktop version. mockViewport(width) simulates a screen width for useMediaQuery.
import { vi } from 'vitest';

/** @param {number} width - in CSS pixels, e.g. 360 for a phone */
export function mockViewport(width) {
  vi.stubGlobal('matchMedia', (query) => {
    const max = Number(/max-width:\s*(\d+)px/.exec(query)?.[1] ?? Infinity);
    const min = Number(/min-width:\s*(\d+)px/.exec(query)?.[1] ?? 0);
    return {
      matches: width <= max && width >= min,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    };
  });
}
