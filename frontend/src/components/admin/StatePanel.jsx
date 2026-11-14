// src/components/admin/StatePanel.jsx
// Panel shown instead of the table: empty list, loading error, missing rights.
// tone="error" adds the red side border and announces the panel (role="alert").

export default function StatePanel({ title, text, tone = 'neutral', withLogo = false, children }) {
  const isError = tone === 'error';
  return (
    <div className={`state-panel${isError ? ' is-error' : ''}`} role={isError ? 'alert' : undefined}>
      {withLogo && <img className="state-panel-logo" src="/assets/Logo.svg" alt="" aria-hidden="true" />}
      <h2 className="state-panel-title">{title}</h2>
      {text && <p className="state-panel-text">{text}</p>}
      {children}
    </div>
  );
}
