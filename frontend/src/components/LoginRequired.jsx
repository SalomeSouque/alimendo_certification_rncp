// src/components/LoginRequired.jsx
// Carte "connexion requise" affichée à la place d'une feature protégée.
// Purement présentationnel : aucune logique d'auth ici.
//
// Note : les styles inline utilisent les design tokens de common.css
// (var(--green), var(--border), var(--ink)) avec un fallback, pour rester
// cohérent avec le reste du site sans dépendre d'une nouvelle feuille de style.
// Tu peux tout à fait déplacer ces styles dans common.css si tu préfères.

import { Link, useLocation } from 'react-router-dom';

// Libellés lisibles par feature (fallback générique sinon).
const FEATURE_LABELS = {
  'aliment-frais': 'l’analyse d’un aliment frais par photo',
  chatbot: 'le chatbot',
};

export default function LoginRequired({ feature }) {
  const location = useLocation();
  const label = FEATURE_LABELS[feature] ?? 'cette fonctionnalité';

  return (
    <main className="auth-main">
      <div className="auth-card">
        <img className="auth-logo" src="/assets/Logo.svg" alt="Logo Alimendo" />
        <h1 className="auth-title">
            Oups, connexion requise
        </h1>
        <p className="auth-subtitle">
          Pour utiliser {label}, il faut être connecté.e à un compte.
        </p>

        <Link
          to="/connexion"
          // On mémorise la page d'origine pour y revenir après connexion.
          state={{ from: location.pathname }}
          className="btn-primary auth-submit"
        >
          Se connecter
        </Link>

        <p>
          <Link to="/" className="btn-back">
            Retour à l’accueil
          </Link>
        </p>
      </div>
    </main>
  );
}
