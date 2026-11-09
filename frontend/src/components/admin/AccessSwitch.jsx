// src/components/admin/AccessSwitch.jsx
// On/off switch of an account's AI access. A real <button role="switch">:
// keyboard (Space, Enter) and screen readers work without extra code.
// It only reports the click; the confirmation and the API call live in the page.

export default function AccessSwitch({ checked, label, busy = false, disabled = false, describedBy, onToggle }) {
  const classes = ['access-switch', checked && 'is-on', busy && 'is-busy'].filter(Boolean).join(' ');
  return (
    <button
      type="button"
      role="switch"
      className={classes}
      aria-checked={checked}
      aria-label={label}
      aria-describedby={describedBy}
      aria-busy={busy || undefined}
      disabled={disabled || busy}
      onClick={onToggle}
    >
      <span className="access-switch-knob" aria-hidden="true" />
    </button>
  );
}
