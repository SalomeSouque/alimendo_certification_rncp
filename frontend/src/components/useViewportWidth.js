// src/components/useViewportWidth.js
// Width of the page in CSS pixels (scrollbar excluded), updated on resize.

import { useSyncExternalStore } from 'react';

function subscribe(onChange) {
  window.addEventListener('resize', onChange);
  // The vertical scrollbar can appear without a resize event (page content loading):
  // the root element changes size, so a ResizeObserver catches it.
  const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(onChange) : null;
  observer?.observe(document.documentElement);
  return () => {
    window.removeEventListener('resize', onChange);
    observer?.disconnect();
  };
}

/** @returns {number} 0 when there is no layout (jsdom): callers keep their default. */
export function useViewportWidth() {
  return useSyncExternalStore(subscribe, () => document.documentElement.clientWidth, () => 0);
}
