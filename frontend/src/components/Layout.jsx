import { NavLink, Link } from 'react-router-dom';
import Header from '../components/Header.jsx';

export default function Layout({ children, wave = null }) {
  return (
    <div className="frame">
      {wave}

      <Header />

      {children}

      <footer className="footer">
        <div className="footer-logo">
          <img src="/assets/Logo.svg" alt="Logo Alimendo" />
          <span className="footer-brand">ALIMENDO</span>
        </div>
        <div className="footer-links">
          <NavLink to="/en-savoir-plus">En savoir plus</NavLink>
          <a href="#">Ressources</a>
          <NavLink to="/chatbot">Chatbot</NavLink>
        </div>
        <p className="footer-disclaimer">
          Cet outil ne remplace pas un suivi médical. Consultez un professionnel de santé
          pour toute décision relative à votre pathologie.
        </p>
        <p className="footer-copyright">© 2026 Alimendo - Projet étudiant</p>
      </footer>

      <Link to="/chatbot" className="chat-fab">
        <img src="/assets/interrogation.svg" alt="" />Une question ?
      </Link>
    </div>
  );
}