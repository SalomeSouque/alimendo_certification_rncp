// src/context/AuthProvider.jsx
import { useEffect, useRef, useState, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import * as authService from '../services/auth';
import { SESSION_EXPIRED_EVENT } from '../services/api';
import { AuthContext } from './AuthContext';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  // Refs so the event listener always reads current values without
  // being re-registered on every render.
  const userRef = useRef(user);
  const pathRef = useRef(location.pathname);
  useEffect(() => { userRef.current = user; }, [user]);
  useEffect(() => { pathRef.current = location.pathname; }, [location.pathname]);

  // Session restore on app start.
  useEffect(() => {
    let active = true;
    authService
      .fetchCurrentUser()
      .then((currentUser) => { if (active) setUser(currentUser); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  // Central handling of expired sessions (401 on an authenticated call).
  // api.js already removed the token; here we update the state and redirect.
  useEffect(() => {
    function onSessionExpired() {
      const wasLoggedIn = userRef.current !== null;
      setUser(null);
      // A stale token found at startup is cleaned silently: no redirect
      // when the user was not considered logged in.
      if (wasLoggedIn && pathRef.current !== '/connexion') {
        navigate('/connexion', {
          replace: true,
          state: { from: pathRef.current, reason: 'expired' },
        });
      }
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
  }, [navigate]);

  const login = useCallback(async (email, password) => {
    const { user: loggedUser } = await authService.login(email, password);
    setUser(loggedUser);
    return loggedUser;
  }, []);

  const register = useCallback(async (email, password, consent) => {
    const { user: newUser } = await authService.register(email, password, consent);
    setUser(newUser);
    return newUser;
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  const value = { user, isAuthenticated: Boolean(user), loading, login, register, logout };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}