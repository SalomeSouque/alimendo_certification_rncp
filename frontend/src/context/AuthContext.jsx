// src/context/AuthContext.jsx
// État d'authentification GLOBAL, partagé par toute l'app via React Context.
//
// Pourquoi un contexte plutôt qu'une variable par page ?
// Parce que "l'utilisateur est-il connecté ?" est une info transverse : le header,
// le gating des pages IA, la page /connexion... tous doivent voir la MÊME valeur.
// Un contexte = une seule source de vérité, mise à jour à un seul endroit.

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from 'react';
import * as authService from '../services/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // user = null quand déconnecté, objet { id, email, role } quand connecté.
  const [user, setUser] = useState(null);
  // loading = true tant qu'on n'a pas vérifié le token au chargement de l'app.
  // Sert à éviter un "flash" de contenu incorrect avant de savoir si on est connecté.
  const [loading, setLoading] = useState(true);

  // Au montage : si un token existe déjà (ex. après un refresh de page),
  // on restaure la session en récupérant l'utilisateur courant.
  useEffect(() => {
    let active = true; // garde anti "setState après démontage"
    authService
      .fetchCurrentUser()
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
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

  const value = {
    user,
    isAuthenticated: Boolean(user),
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook d'accès à l'état d'auth.
 * Usage : const { isAuthenticated, user, login, logout } = useAuth();
 */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error('useAuth doit être utilisé à l’intérieur de <AuthProvider>.');
  }
  return ctx;
}
