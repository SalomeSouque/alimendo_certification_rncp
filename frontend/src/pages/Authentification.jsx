import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout.jsx';
import './Authentification.css';

export default function Authentification() {
  // État : le mot de passe est-il affiché en clair ?
  const [motDePasseVisible, setMotDePasseVisible] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const wave = (
    <img
      className="wave wave-auth"
      src="/assets/yellow_line_identification_page.svg"
      alt=""
      aria-hidden="true"
    />
  );

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(identifier, password);
      // Retour vers la page d'origine (posée par LoginRequired), sinon accueil.
      const from = location.state?.from ?? '/';
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Layout wave={wave}>
      <main className="auth-main">
        <div className="auth-card">
          <img className="auth-logo" src="/assets/Logo.svg" alt="Logo Alimendo" />
          <h1 className="auth-title">
            Oups, cette fonctionnalité<br />demande un compte.
          </h1>
          <p className="auth-subtitle">Connectez-vous pour y accéder.</p>

          <form onSubmit={handleSubmit}>
            <div className="field">
            <label htmlFor="identifiant">Identifiant</label>
              <div className="input-wrap">
                <input value={identifier} onChange={(e) => setIdentifier(e.target.value)} />
              </div>
            </div>

            <div className="field">
              <label htmlFor="motdepasse">Mot de passe</label>
              <div className="input-wrap">
                <input
                  type={motDePasseVisible ? 'text' : 'password'}
                  value={password} onChange={(e) => setPassword(e.target.value)}
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
            {error && <p role="alert" style={{ color: 'crimson' }}>{error}</p>}

            <button className="btn-primary auth-submit" type="submit" disabled={submitting}>
              {submitting ? 'Connexion…' : 'Se connecter'}
            </button>
          </form>

          <Link to="/" className="btn-back">Retour à l'accueil</Link>
        </div>
      </main>
    </Layout>
  );
}