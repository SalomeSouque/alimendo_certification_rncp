import { useId, useRef, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { PASSWORD_MIN_LENGTH } from '../services/auth';
import Layout from '../components/Layout.jsx';
import './Authentification.css';

// Simple format check, the backend (EmailStr) stays the reference.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Maps an ApiError to a message for the form.
 * @param {any} err
 * @param {'login'|'register'} mode
 */
function errorMessage(err, mode) {
  if (err?.status === 422) {
    return mode === 'register'
      ? 'Vérifiez l’email, le mot de passe (8 caractères minimum) et la case de consentement.'
      : 'Vérifiez l’email et le mot de passe saisis.';
  }
  return err?.message ?? 'Une erreur est survenue. Réessayez.';
}

/**
 * Login page (/connexion) and sign-up page (/inscription).
 * The mode comes from the URL so each form has its own link.
 */
export default function Authentification() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const mode = location.pathname === '/inscription' ? 'register' : 'login';
  const isRegister = mode === 'register';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [consent, setConsent] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const emailRef = useRef(null);
  const passwordRef = useRef(null);
  const consentRef = useRef(null);
  const ids = {
    email: useId(),
    password: useId(),
    passwordHint: useId(),
    consent: useId(),
    emailError: useId(),
    passwordError: useId(),
    consentError: useId(),
  };

  const sessionExpired = location.state?.reason === 'expired';
  // Keep the page of origin when switching between login and sign-up.
  const from = location.state?.from ?? '/';

  /** @returns {Record<string, string>} errors per field, empty when valid. */
  function validate() {
    const errors = {};
    if (!EMAIL_PATTERN.test(email.trim())) {
      errors.email = 'Saisissez une adresse email valide (exemple : nom@domaine.fr).';
    }
    if (!password) {
      errors.password = 'Saisissez votre mot de passe.';
    } else if (isRegister && password.length < PASSWORD_MIN_LENGTH) {
      errors.password = `Le mot de passe doit contenir au moins ${PASSWORD_MIN_LENGTH} caractères.`;
    }
    if (isRegister && !consent) {
      errors.consent = 'Cochez la case pour créer votre compte.';
    }
    return errors;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    const errors = validate();
    setFieldErrors(errors);
    if (errors.email) return emailRef.current?.focus();
    if (errors.password) return passwordRef.current?.focus();
    if (errors.consent) return consentRef.current?.focus();

    setSubmitting(true);
    try {
      if (isRegister) {
        await register(email, password, consent);
      } else {
        await login(email, password);
      }
      navigate(from, { replace: true });
    } catch (err) {
      setError(errorMessage(err, mode));
    } finally {
      setSubmitting(false);
    }
  }

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
          <img className="auth-logo" src="/assets/Logo.svg" alt="" aria-hidden="true" />
          <h1 className="auth-title">{isRegister ? 'Créer un compte' : 'Connexion'}</h1>

          {sessionExpired && !isRegister && (
            <p className="auth-notice" role="status">
              Votre session a expiré. Reconnectez-vous pour reprendre là où vous en étiez.
            </p>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="field">
              <label htmlFor={ids.email}>Email</label>
              <div className="input-wrap">
                <input
                  id={ids.email}
                  ref={emailRef}
                  type="email"
                  autoComplete="email"
                  inputMode="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  aria-invalid={Boolean(fieldErrors.email)}
                  aria-describedby={fieldErrors.email ? ids.emailError : undefined}
                  required
                />
              </div>
              {fieldErrors.email && (
                <p id={ids.emailError} className="field-error">{fieldErrors.email}</p>
              )}
            </div>

            <div className="field">
              <label htmlFor={ids.password}>Mot de passe</label>
              <div className="input-wrap input-wrap--password">
                <input
                  id={ids.password}
                  ref={passwordRef}
                  type={passwordVisible ? 'text' : 'password'}
                  autoComplete={isRegister ? 'new-password' : 'current-password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={Boolean(fieldErrors.password)}
                  aria-describedby={
                    [isRegister ? ids.passwordHint : null, fieldErrors.password ? ids.passwordError : null]
                      .filter(Boolean)
                      .join(' ') || undefined
                  }
                  required
                />
                <button
                  type="button"
                  className="toggle-eye"
                  aria-label={passwordVisible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                  aria-pressed={passwordVisible}
                  onClick={() => setPasswordVisible((v) => !v)}
                >
                  <img
                    src={passwordVisible ? '/assets/eye_close.svg' : '/assets/eye_open.svg'}
                    alt=""
                    aria-hidden="true"
                  />
                </button>
              </div>
              {isRegister && (
                <p id={ids.passwordHint} className="field-hint">
                  {PASSWORD_MIN_LENGTH} caractères minimum.
                </p>
              )}
              {fieldErrors.password && (
                <p id={ids.passwordError} className="field-error">{fieldErrors.password}</p>
              )}
            </div>

            {isRegister && (
              <div className="field field--checkbox">
                <input
                  id={ids.consent}
                  ref={consentRef}
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  aria-invalid={Boolean(fieldErrors.consent)}
                  aria-describedby={fieldErrors.consent ? ids.consentError : undefined}
                  required
                />
                <label htmlFor={ids.consent}>
                  J’accepte qu’Alimendo enregistre mon email pour gérer mon compte. Je comprends
                  qu’avoir un compte sur un site consacré à l’endométriose peut révéler une
                  information sur ma santé. Je peux retirer ce consentement à tout moment en
                  demandant la suppression de mon compte.
                </label>
                {fieldErrors.consent && (
                  <p id={ids.consentError} className="field-error">{fieldErrors.consent}</p>
                )}
              </div>
            )}

            {error && <p role="alert" className="form-error">{error}</p>}

            <button className="btn-primary auth-submit" type="submit" disabled={submitting}>
              {submitting
                ? (isRegister ? 'Création du compte…' : 'Connexion…')
                : (isRegister ? 'Créer mon compte' : 'Se connecter')}
            </button>
          </form>

          <p className="auth-switch">
            {isRegister ? 'Déjà un compte ? ' : 'Pas encore de compte ? '}
            <Link to={isRegister ? '/connexion' : '/inscription'} state={{ from }}>
              {isRegister ? 'Se connecter' : 'Créer un compte'}
            </Link>
          </p>

          <Link to="/" className="btn-back">Retour à l'accueil</Link>
          {/* GDPR information notice (art. 13). Details: docs/rgpd/ */}
          <p className="auth-rgpd">
            Votre email sert uniquement à vous connecter à Alimendo : il n'est ni partagé
            ni utilisé à d'autres fins. Votre compte est supprimé après 3 ans sans connexion,
            ou plus tôt sur simple demande auprès de l'administratrice du site.
          </p>
        </div>
      </main>
    </Layout>
  );
}