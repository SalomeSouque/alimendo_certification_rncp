// src/components/admin/AccountTable.jsx
// Accounts table of the admin space: email, signup date, AI access.
// A real <table> (the mockups used divs only for the Figma export).
// Minimal data only (GDPR): no last login, no health data.

import { ROLE_ADMIN } from '../../services/admin';
import AccessSwitch from './AccessSwitch';

const DATE_FORMAT = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });

/** @param {string} iso */
function formatDate(iso) {
  return DATE_FORMAT.format(new Date(iso));
}

function AccessState({ open, busy }) {
  if (busy) return <span className="access-state is-pending">Mise à jour…</span>;
  return open
    ? <span className="access-state is-on">Ouvert</span>
    : <span className="access-state is-off">Fermé</span>;
}

function AccountRow({ account, isSelf, rowState, onToggle, onRetry }) {
  const busy = Boolean(rowState?.busy);
  const error = rowState?.error;
  const selfHintId = `self-hint-${account.id}`;
  const errorId = `row-error-${account.id}`;

  return (
    <tr className={error ? 'is-error' : undefined}>
      <th scope="row" className="account-email-cell">
        <span className="account-email">{account.email}</span>
        {account.role === ROLE_ADMIN && <span className="account-tag is-admin">admin</span>}
        {isSelf && <span className="account-tag is-self">vous</span>}
      </th>
      <td className="account-date">
        <time dateTime={account.created_at}>{formatDate(account.created_at)}</time>
      </td>
      <td className="account-access-cell">
        <div className="account-access">
          <AccessSwitch
            checked={account.acces_ia}
            busy={busy}
            disabled={isSelf}
            label={`Accès IA de ${account.email}`}
            describedBy={isSelf ? selfHintId : error ? errorId : undefined}
            onToggle={() => onToggle(account)}
          />
          <AccessState open={account.acces_ia} busy={busy} />
        </div>
        {isSelf && (
          <p id={selfHintId} className="account-hint">
            Votre propre accès se modifie avec le script serveur.
          </p>
        )}
        {error && (
          <div id={errorId} className="account-error" role="alert">
            <span>{error}</span>
            <button type="button" className="link-button" onClick={() => onRetry(account)}>
              Réessayer
            </button>
          </div>
        )}
      </td>
    </tr>
  );
}

export default function AccountTable({ accounts, currentUserId, rowStates, onToggle, onRetry }) {
  return (
    <div className="account-table-wrap">
      <table className="account-table">
        <caption className="sr-only">Comptes inscrits et état de leur accès IA</caption>
        <thead>
          <tr>
            <th scope="col">Email</th>
            <th scope="col">Inscription</th>
            <th scope="col">Accès IA</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => (
            <AccountRow
              key={account.id}
              account={account}
              isSelf={account.id === currentUserId}
              rowState={rowStates[account.id]}
              onToggle={onToggle}
              onRetry={onRetry}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
