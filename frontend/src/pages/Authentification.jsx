import { useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import './Authentification.css';

export default function Authentification() {
  // État : le mot de passe est-il affiché en clair ?
  const [motDePasseVisible, setMotDePasseVisible] = useState(false);

  const wave = (
    <img
      className="wave wave-auth"
      src="/assets/yellow_line_identification_page.svg"
      alt=""
      aria-hidden="true"
    />
  );

  return (
    <Layout wave={wave}>
      <main className="auth-main">
        <div className="auth-card">
          <img className="auth-logo" src="/assets/Logo.svg" alt="Logo Alimendo" />
          <h1 className="auth-title">
            Oups, cette fonctionnalité<br />demande un compte.
          </h1>
          <p className="auth-subtitle">Connectez-vous pour y accéder.</p>

          <div className="field">
            <label htmlFor="identifiant">Identifiant</label>
            <div className="input-wrap">
              <input type="text" id="identifiant" autoComplete="username" />
            </div>
          </div>

          <div className="field">
            <label htmlFor="motdepasse">Mot de passe</label>
            <div className="input-wrap">
              <input
                type={motDePasseVisible ? 'text' : 'password'}
                id="motdepasse"
                autoComplete="current-password"
              />
              <button
                type="button"
                className="toggle-eye"
                aria-label={motDePasseVisible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                onClick={() => setMotDePasseVisible((v) => !v)}
              >
                <img src="/assets/eye.svg" alt="" />
              </button>
            </div>
          </div>

          {/* Lien pour l'instant, deviendra un vrai submit au branchement auth */}
          <Link to="/" className="btn-primary auth-submit">Se connecter</Link>

          <Link to="/" className="auth-back">&larr; Retour à l'accueil</Link>
        </div>
      </main>
    </Layout>
  );
}