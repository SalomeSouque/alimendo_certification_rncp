// src/components/useApiResource.js
// Small hook: runs an async loader when its key changes and exposes
// { status: 'loading' | 'success' | 'error', data, error }.
// Ignores the answer of a request that is no longer current (fast navigation).

import { useEffect, useState } from 'react';

export function useApiResource(loader, key) {
  const [state, setState] = useState({ status: 'loading', data: null, error: null, key });

  useEffect(() => {
    if (key == null) return undefined;
    let active = true;
    loader()
      .then((data) => { if (active) setState({ status: 'success', data, error: null, key }); })
      .catch((error) => { if (active) setState({ status: 'error', data: null, error, key }); });
    return () => { active = false; };
    // The key identifies the request; the loader is recreated on each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  // While the new request is in flight, do not show the previous result.
  return state.key === key ? state : { status: 'loading', data: null, error: null, key };
}
