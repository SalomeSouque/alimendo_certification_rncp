// src/components/analyse/CaptureShell.jsx
// Full-screen frame of the mobile analysis (maquettes M3a to M3e):
// ✕ to leave, content, and the Code-barre / Photo / Écrire tabs at the bottom.
// No site header, footer or "?" bubble on these screens.
//
//   tone="dark"  camera screens: content = the camera stage, `bottom` = actions under the tabs
//   tone="light" "Écrire" tab: a top bar with ✕ and the title, tabs fixed at the bottom

import { NavLink, useNavigate } from 'react-router-dom';
import { CloseIcon } from '../icons.jsx';
import './CaptureShell.css';

const TABS = [
  { to: '/produit-emballe', label: 'Code-barre' },
  { to: '/aliment-frais', label: 'Photo' },
  { to: '/recherche', label: 'Écrire' },
];

/** Bottom tabs. `replace`: switching tabs does not pile up history entries. */
function CaptureTabs() {
  return (
    <nav className="capture-tabs" aria-label="Mode d’analyse">
      {TABS.map((tab) => (
        <NavLink key={tab.to} to={tab.to} replace className="capture-tab">
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}

/** ✕: leaves the analysis, back to the home page. */
function CloseButton({ className }) {
  const navigate = useNavigate();
  return (
    <button type="button" className={className} aria-label="Quitter l’analyse" onClick={() => navigate('/')}>
      <CloseIcon />
    </button>
  );
}

/**
 * @param {{
 *   tone: 'dark'|'light',
 *   title: string,          visible title (light) or screen-reader title (dark)
 *   topRight?: React.ReactNode,  dark only: action at the top right (torch)
 *   bottom?: React.ReactNode,    dark only: actions and note under the tabs
 *   stageClassName?: string,     dark only: extra class on the camera area
 *   children: React.ReactNode,
 * }} props
 */
export default function CaptureShell({ tone, title, topRight = null, bottom = null, stageClassName = '', children }) {
  if (tone === 'light') {
    return (
      <div className="capture capture--light">
        <header className="capture-bar">
          <CloseButton className="capture-bar-close" />
          <h1 className="capture-bar-title">{title}</h1>
        </header>
        <main className="capture-content">{children}</main>
        <div className="capture-tabs-wrap">
          <CaptureTabs />
        </div>
      </div>
    );
  }

  return (
    <div className="capture capture--dark">
      <main className={`capture-stage ${stageClassName}`.trim()}>
        <h1 className="sr-only">{title}</h1>
        {children}
        <CloseButton className="capture-round capture-round--left" />
        {topRight}
      </main>
      <div className="capture-panel">
        <CaptureTabs />
        {bottom}
      </div>
    </div>
  );
}
