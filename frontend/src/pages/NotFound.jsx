import { Link } from 'react-router-dom';
import './NotFound.css';

/**
 * Page shown for any unknown address (route *). Same card as the maintenance page
 * (deploy/maintenance/index.html), with a way back to the home page.
 */
export default function NotFound() {
  return (
    <div className="notfound-frame">
      <img className="notfound-wave" src="/assets/yellow_line_identification_page.svg" alt="" aria-hidden="true" data-bleed />

      <main className="notfound-card">
        <img className="notfound-logo" src="/assets/Logo.svg" alt="Alimendo" />
        <p className="notfound-tagline">alimentation &amp; endométriose, en clair</p>

        <h1 className="notfound-title">Erreur 404</h1>
        <p className="notfound-message">Oups, cette page n’existe pas.</p>
        <Link to="/" className="btn-primary notfound-button">Retour à l’accueil</Link>

        <p className="notfound-copyright">© 2026 Alimendo · Projet étudiant</p>
      </main>
    </div>
  );
}
