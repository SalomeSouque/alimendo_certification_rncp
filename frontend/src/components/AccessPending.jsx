// src/components/AccessPending.jsx
// Card shown when /ai/* answers 403: the account exists but its AI access
// has not been approved yet by an admin. Presentational only.

import { Link } from 'react-router-dom';
import '../pages/Authentification.css';

export default function AccessPending() {
  return (
    <div className="auth-card" role="status">
      <img className="auth-logo" src="/assets/Logo.svg" alt="" aria-hidden="true" />
      <h2 className="auth-title">Accès en attente de validation</h2>
      <p className="auth-subtitle">
        Votre compte est bien créé. Le chatbot et l’analyse photo utilisent des services
        d’IA payants : leur accès est ouvert compte par compte par l’administratrice du site.
      </p>
      <p>En attendant, la recherche par nom et le score des aliments restent accessibles.</p>
      <p>
        <Link to="/analyser" className="btn-primary auth-submit">Rechercher un aliment</Link>
      </p>
      <p className="disclaimer-mention">Projet étudiant</p>
    </div>
  );
}
