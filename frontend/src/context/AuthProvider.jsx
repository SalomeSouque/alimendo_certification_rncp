// src/context/AuthProvider.jsx
import { useEffect, useState, useCallback } from 'react';
import * as authService from '../services/auth';
import { AuthContext } from './AuthContext';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    authService
      .fetchCurrentUser()
      .then((currentUser) => { if (active) setUser(currentUser); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const login = useCallback(async (identifier, password) => {
    const { user: loggedUser } = await authService.login(identifier, password);
    setUser(loggedUser);
    return loggedUser;
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  const value = { user, isAuthenticated: Boolean(user), loading, login, logout };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}