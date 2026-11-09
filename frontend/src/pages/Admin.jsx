// src/pages/Admin.jsx
// Admin space v1 (/admin, lot 37): open or close the AI access of each account.
// GET /admin/utilisateurs for the list, PATCH /admin/utilisateurs/{id}/acces-ia
// for a change, always after a confirmation. Route guarded by AdminRoute.

import { useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import Toast from '../components/Toast.jsx';
import AccountFilter from '../components/admin/AccountFilter.jsx';
import AccountTable from '../components/admin/AccountTable.jsx';
import StatePanel from '../components/admin/StatePanel.jsx';
import { countByFilter, filterAccounts } from '../components/admin/accountFilters';
import { useApiResource } from '../components/useApiResource';
import { useAuth } from '../context/AuthContext';
import { listAccounts, setAiAccess } from '../services/admin';
import './Admin.css';

const EMPTY_STATES = {
  pending: {
    title: 'Aucun compte à valider',
    text: 'Tous les comptes inscrits ont déjà un accès ouvert.',
  },
  open: {
    title: 'Aucun accès ouvert',
    text: 'Aucun compte n’a encore accès au chatbot ni à l’analyse photo.',
  },
  all: {
    title: 'Aucun compte inscrit',
    text: 'Les comptes apparaîtront ici après leur inscription.',
  },
};

/** @param {number} n */
function accountsLabel(n) {
  return `${n} compte${n > 1 ? 's' : ''}`;
}

function ListSkeleton() {
  return (
    <div className="state-panel is-skeleton" role="status">
      <span className="sr-only">Chargement des comptes…</span>
      {[100, 75, 85].map((width) => (
        <div key={width} className="skeleton-row" aria-hidden="true">
          <span className="skeleton-bar" style={{ maxWidth: `${width}%` }} />
          <span className="skeleton-switch" />
        </div>
      ))}
    </div>
  );
}

export default function Admin() {
  const { user } = useAuth();
  const [reloadKey, setReloadKey] = useState(0);
  const { status, data, error } = useApiResource(listAccounts, reloadKey);

  // Accounts returned by a successful PATCH, by id: they override the loaded list.
  const [updated, setUpdated] = useState({});
  // Per-row state: { busy: true } during the PATCH, { error, target } after a failure.
  const [rowStates, setRowStates] = useState({});
  const [filter, setFilter] = useState('pending');
  const [term, setTerm] = useState('');
  const [confirming, setConfirming] = useState(null);
  const [toast, setToast] = useState(null);
  const [forbidden, setForbidden] = useState(false);

  const accounts = (data ?? []).map((account) => updated[account.id] ?? account);
  const counts = countByFilter(accounts);
  const visible = filterAccounts(accounts, filter, term);
  const shownLabel = visible.length === accounts.length
    ? accountsLabel(accounts.length)
    : `${accountsLabel(visible.length)} sur ${accounts.length}`;

  function setRowState(id, value) {
    setRowStates((states) => ({ ...states, [id]: value }));
  }

  function reload() {
    setUpdated({});
    setRowStates({});
    setReloadKey((key) => key + 1);
  }

  async function applyAccess(account, enabled) {
    setRowState(account.id, { busy: true });
    try {
      const result = await setAiAccess(account.id, enabled);
      setUpdated((previous) => ({ ...previous, [result.id]: result }));
      setRowState(account.id, null);
      setToast((previous) => ({
        id: (previous?.id ?? 0) + 1,
        text: `${enabled ? 'Accès ouvert' : 'Accès fermé'} pour ${result.email}`,
      }));
    } catch (err) {
      // 401 is handled by api.js (redirect to the login page).
      if (err.status === 403) {
        setForbidden(true);
        return;
      }
      setRowState(account.id, { error: `${err.message} L’accès n’a pas changé.`, target: enabled });
    }
  }

  function confirmChange() {
    const account = confirming;
    setConfirming(null);
    applyAccess(account, !account.acces_ia);
  }

  function renderList() {
    if (status === 'loading') return <ListSkeleton />;

    if (status === 'error') {
      return (
        <StatePanel tone="error" title="Impossible de charger les comptes" text={error?.message}>
          <button type="button" className="btn-primary btn-small" onClick={reload}>Réessayer</button>
        </StatePanel>
      );
    }

    if (visible.length === 0) {
      if (term.trim()) {
        return (
          <StatePanel withLogo title={`Aucun compte ne correspond à « ${term.trim()} »`}>
            <button type="button" className="btn-secondary btn-small" onClick={() => setTerm('')}>
              Effacer la recherche
            </button>
          </StatePanel>
        );
      }
      const empty = EMPTY_STATES[filter];
      return (
        <StatePanel withLogo title={empty.title} text={empty.text}>
          {filter !== 'all' && (
            <button type="button" className="btn-secondary btn-small" onClick={() => setFilter('all')}>
              Voir tous les comptes
            </button>
          )}
        </StatePanel>
      );
    }

    return (
      <>
        <AccountTable
          accounts={visible}
          currentUserId={user?.id}
          rowStates={rowStates}
          onToggle={setConfirming}
          onRetry={(account) => applyAccess(account, rowStates[account.id].target)}
        />
        <div className="admin-footnote">
          <p>{`${shownLabel}, du plus récent au plus ancien`}</p>
          <p>Affiché : email et date d’inscription uniquement (minimisation RGPD)</p>
        </div>
      </>
    );
  }

  // Error a GET or a PATCH answered with 403: the admin role was removed meanwhile.
  const noRights = forbidden || (status === 'error' && error?.status === 403);

  return (
    <Layout>
      <main className="admin-main">
        <p className="step-label">Back-office</p>
        <h1 className="section-title admin-title">Espace admin</h1>
        <p className="section-body admin-lead">
          Ouvrez ou fermez, compte par compte, l’accès au chatbot et à l’analyse d’un aliment
          frais par photo.
        </p>

        <div className="admin-notice">
          <p className="admin-notice-title">Projet étudiant, prototype de démonstration.</p>
          <p>
            Chaque accès ouvert peut consommer des crédits Mistral payés par le projet :
            ouvrez-le uniquement aux comptes que vous connaissez (jury, testeuses).
          </p>
        </div>

        {noRights ? (
          <StatePanel
            withLogo
            title="Accès réservé aux admins"
            text="Votre compte n’a plus les droits nécessaires pour cette page."
          >
            <Link to="/" className="btn-secondary btn-small">Retour à l’accueil</Link>
          </StatePanel>
        ) : (
          <>
            <div className="admin-toolbar">
              <AccountFilter value={filter} counts={counts} onChange={setFilter} />
              <div className="admin-search">
                <img src="/assets/loupe.svg" alt="" aria-hidden="true" />
                <input
                  type="search"
                  aria-label="Rechercher un email"
                  placeholder="Rechercher un email"
                  value={term}
                  onChange={(e) => setTerm(e.target.value)}
                />
              </div>
            </div>
            {renderList()}
          </>
        )}
      </main>

      {confirming && (
        <ConfirmDialog
          title={confirming.acces_ia ? 'Fermer l’accès IA ?' : 'Ouvrir l’accès IA ?'}
          confirmLabel={confirming.acces_ia ? 'Fermer l’accès' : 'Ouvrir l’accès'}
          tone={confirming.acces_ia ? 'danger' : 'primary'}
          onConfirm={confirmChange}
          onCancel={() => setConfirming(null)}
        >
          {confirming.acces_ia ? (
            <>
              <p>
                Effet immédiat : la prochaine requête de <strong>{confirming.email}</strong> au
                chatbot ou à l’analyse photo sera refusée.
              </p>
              <p>Vous pourrez rouvrir l’accès à tout moment.</p>
            </>
          ) : (
            <>
              <p>
                <strong>{confirming.email}</strong> pourra utiliser le chatbot et l’analyse d’un
                aliment frais par photo.
              </p>
              <p>Chaque requête consomme des crédits Mistral payés par le projet.</p>
            </>
          )}
        </ConfirmDialog>
      )}

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </Layout>
  );
}
