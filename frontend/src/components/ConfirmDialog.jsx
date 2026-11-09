// src/components/ConfirmDialog.jsx
// Modal confirmation dialog (WAI-ARIA "alertdialog" pattern).
// Not the native <dialog>: jsdom does not implement showModal(), so the tests
// could not open it. Focus handling is done here instead:
//   - focus goes to "Annuler" on open (the safe choice for a destructive action);
//   - Tab and Shift+Tab stay inside the dialog;
//   - Escape cancels;
//   - focus goes back to the element that opened the dialog on close.

import { useEffect, useId, useRef } from 'react';
import './ConfirmDialog.css';

export default function ConfirmDialog({
  title,
  children,
  confirmLabel,
  cancelLabel = 'Annuler',
  tone = 'primary',
  onConfirm,
  onCancel,
}) {
  const titleId = useId();
  const textId = useId();
  const dialogRef = useRef(null);
  const cancelRef = useRef(null);

  useEffect(() => {
    const opener = document.activeElement;
    cancelRef.current?.focus();
    return () => opener?.focus?.();
  }, []);

  function handleKeyDown(e) {
    if (e.key === 'Escape') {
      e.stopPropagation();
      onCancel();
      return;
    }
    if (e.key !== 'Tab') return;
    const buttons = dialogRef.current.querySelectorAll('button:not([disabled])');
    const first = buttons[0];
    const last = buttons[buttons.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="dialog-overlay" onMouseDown={(e) => e.target === e.currentTarget && onCancel()}>
      <div
        ref={dialogRef}
        className="dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={textId}
        onKeyDown={handleKeyDown}
      >
        <h2 id={titleId} className="dialog-title">{title}</h2>
        <div id={textId} className="dialog-text">{children}</div>
        <div className="dialog-actions">
          <button ref={cancelRef} type="button" className="btn-secondary btn-small" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={`${tone === 'danger' ? 'btn-danger' : 'btn-primary'} btn-small`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
