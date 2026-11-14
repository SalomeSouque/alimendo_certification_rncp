// src/components/Toast.jsx
// Short confirmation message that hides itself after `duration` ms.
// The live region stays mounted so screen readers announce every new message.
//
// Usage: <Toast toast={{ id, text }} onDismiss={() => setToast(null)} />
// A new `id` restarts the timer, even when the text is the same.

import { useEffect } from 'react';
import './Toast.css';

export default function Toast({ toast, onDismiss, duration = 4000 }) {
  useEffect(() => {
    if (!toast) return undefined;
    const timer = setTimeout(onDismiss, duration);
    return () => clearTimeout(timer);
    // onDismiss is recreated on each parent render: only a new toast restarts the timer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toast?.id, duration]);

  return (
    <div className="toast-region" role="status" aria-live="polite">
      {toast && (
        <div className="toast">
          <svg className="toast-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M5 12.5l4.5 4.5L19 7.5" />
          </svg>
          <span>{toast.text}</span>
        </div>
      )}
    </div>
  );
}
