// src/components/NavDrawer.jsx
// Navigation drawer of the mobile header (maquette M1).
// Modal dialog: focus kept inside, Escape / ✕ / tap on the dimmed background /
// swipe to the left closes it, the page behind does not scroll.

import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { isAdmin } from '../services/admin';
import { CloseIcon, UserIcon } from './icons.jsx';

const LINKS = [
  { to: '/', label: 'Accueil', end: true },
  { to: '/analyser', label: 'Analyser un aliment' },
  { to: '/chatbot', label: 'Chatbot' },
  { to: '/en-savoir-plus', label: 'En savoir plus' },
];

const SWIPE_CLOSE_PX = 60;
const FOCUSABLE = 'a[href], button:not([disabled])';

/** @param {{ onClose: () => void }} props */
export default function NavDrawer({ onClose }) {
  const { user, isAuthenticated, logout } = useAuth();
  const panelRef = useRef(null);
  const touchStartX = useRef(null);
  const onCloseRef = useRef(onClose);
  useEffect(() => { onCloseRef.current = onClose; }, [onClose]);

  // Focus inside on open, lock the page scroll while open.
  useEffect(() => {
    panelRef.current?.querySelector(FOCUSABLE)?.focus();
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previous; };
  }, []);

  function handleKeyDown(e) {
    if (e.key === 'Escape') {
      e.stopPropagation();
      onCloseRef.current();
      return;
    }
    if (e.key !== 'Tab') return;
    const items = [...panelRef.current.querySelectorAll(FOCUSABLE)];
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  function handleTouchEnd(e) {
    if (touchStartX.current === null) return;
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    touchStartX.current = null;
    if (dx < -SWIPE_CLOSE_PX) onClose();
  }

  function handleLogout() {
    logout();
    onClose();
  }

  return createPortal(
    <div className="drawer-root">
      <div className="drawer-backdrop" onClick={onClose} aria-hidden="true" />
      <div
        id="nav-drawer"
        ref={panelRef}
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Menu"
        onKeyDown={handleKeyDown}
        onTouchStart={(e) => { touchStartX.current = e.touches[0].clientX; }}
        onTouchEnd={handleTouchEnd}
      >
        <div className="drawer-top">
          <span className="drawer-brand">
            <img src="/assets/Logo.svg" alt="" />
            <span>ALIMENDO</span>
          </span>
          <button type="button" className="header-m-icon" aria-label="Fermer le menu" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>
        <p className="drawer-tagline">alimentation &amp; endométriose, en clair</p>

        <nav aria-label="Navigation principale">
          <ul className="drawer-links">
            {LINKS.map((link) => (
              <li key={link.to}>
                <NavLink to={link.to} end={link.end} onClick={onClose}>{link.label}</NavLink>
              </li>
            ))}
            {isAdmin(user) && (
              <li><NavLink to="/admin" onClick={onClose}>Admin</NavLink></li>
            )}
          </ul>
          <div className="drawer-account">
            {isAuthenticated ? (
              <button type="button" className="drawer-account-link" onClick={handleLogout}>
                <UserIcon size={20} />Se déconnecter
              </button>
            ) : (
              <NavLink to="/connexion" className="drawer-account-link" onClick={onClose}>
                <UserIcon size={20} />Se connecter
              </NavLink>
            )}
          </div>
        </nav>

        <p className="drawer-note">Projet étudiant · cet outil ne remplace pas un suivi médical.</p>
      </div>
    </div>,
    document.body,
  );
}
