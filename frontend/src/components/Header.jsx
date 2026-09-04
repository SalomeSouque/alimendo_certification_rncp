import { useAuth } from '../context/AuthContext';
import { NavLink, Link } from 'react-router-dom';

export default function Header() {
  const { isAuthenticated, logout } = useAuth();
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
        {/* <NavLink to="/connexion" className={() => 'btn-connect'}>Se connecter</NavLink> */}
        {isAuthenticated
        ? <button onClick={logout} className="btn-auth" >Se déconnecter</button>
        : <NavLink to="/connexion" className="btn-auth" >Se connecter</NavLink>} 
    </nav>
    </header>
    )
}
