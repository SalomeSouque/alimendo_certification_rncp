import { useRef, useState } from 'react';
import { NavLink, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { isAdmin } from '../services/admin';
import { COMPACT_HEADER_QUERY } from '../config/breakpoints';
import { useMediaQuery } from './useMediaQuery';
import NavDrawer from './NavDrawer.jsx';
import { MenuIcon, UserIcon } from './icons.jsx';
import './Header.css';

/** Site header: full navigation on desktop, burger + drawer below 1280 px (maquette M1). */
export default function Header() {
  const compact = useMediaQuery(COMPACT_HEADER_QUERY);
  return compact ? <MobileHeader /> : <DesktopHeader />;
}

function DesktopHeader() {
  const { user, isAuthenticated, logout } = useAuth();
  return (
    <header className="header">
      <div className="header-logo">
        <img src="/assets/Logo.svg" alt="Logo Alimendo" />
      </div>
      <Link to="/" className="header-brand">ALIMENDO</Link>
      <span className="header-tagline">alimentation &amp; endométriose, en clair</span>
      <nav className="header-nav">
        <NavLink to="/">Accueil</NavLink>
        <NavLink to="/analyser">Analyser un aliment</NavLink>
        <NavLink to="/chatbot">Chatbot</NavLink>
        <NavLink to="/en-savoir-plus">En savoir plus</NavLink>
        {isAdmin(user) && <NavLink to="/admin">Admin</NavLink>}
        {isAuthenticated
          ? <button onClick={logout} className="btn-auth">Se déconnecter</button>
          : <NavLink to="/connexion" className="btn-auth">Se connecter</NavLink>}
      </nav>
    </header>
  );
}

function MobileHeader() {
  const { isAuthenticated } = useAuth();
  const [open, setOpen] = useState(false);
  const menuButtonRef = useRef(null);

  function close() {
    setOpen(false);
    menuButtonRef.current?.focus();
  }

  return (
    <header className="header-m">
      <button
        ref={menuButtonRef}
        type="button"
        className="header-m-icon"
        aria-label="Ouvrir le menu"
        aria-expanded={open}
        aria-controls="nav-drawer"
        onClick={() => setOpen(true)}
      >
        <MenuIcon />
      </button>

      <Link to="/" className="header-m-brand" aria-label="Alimendo, accueil">
        <img src="/assets/Logo.svg" alt="" />
        <span aria-hidden="true">ALIMENDO</span>
      </Link>

      {/* Signed in: the account icon opens the menu, where "Se déconnecter" is. */}
      {isAuthenticated ? (
        <button
          type="button"
          className="header-m-icon"
          aria-label="Mon compte (ouvre le menu)"
          aria-expanded={open}
          aria-controls="nav-drawer"
          onClick={() => setOpen(true)}
        >
          <UserIcon />
        </button>
      ) : (
        <Link to="/connexion" className="header-m-icon" aria-label="Se connecter">
          <UserIcon />
        </Link>
      )}

      {open && <NavDrawer onClose={close} />}
    </header>
  );
}