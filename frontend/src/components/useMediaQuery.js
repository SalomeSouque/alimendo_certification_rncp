// src/components/useMediaQuery.js
// True while a CSS media query matches, updated when the window is resized
// or the phone is rotated.

import { useCallback, useSyncExternalStore } from 'react';

/**
 * @param {string} query - e.g. '(max-width: 767px)'
 * @returns {boolean} false when matchMedia is not available (jsdom, old browsers):
 *   the desktop layout is the default.
 */
export function useMediaQuery(query) {
  const subscribe = useCallback(
    (onChange) => {
      const list = window.matchMedia?.(query);
      if (!list) return () => {};
      list.addEventListener('change', onChange);
      return () => list.removeEventListener('change', onChange);
    },
    [query],
  );
  const getSnapshot = () => window.matchMedia?.(query).matches ?? false;
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
