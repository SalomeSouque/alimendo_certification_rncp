// src/services/auth.js
// Service d'authentification. C'est LE point de contact entre l'app et "l'idée
// d'être connecté". Les composants n'appellent jamais fetch ou localStorage
// directement pour l'auth : ils passent par ici. Résultat : quand le vrai
// backend arrivera, on ne touche qu'à ce fichier, pas aux pages.

import { api } from './api';
import { getToken, setToken, clearToken } from './token';

// --- Bascule mock <-> vrai backend --------------------------------------
// Tant que FastAPI n'expose pas /auth/login, on reste en mock.
// Piloté par .env : VITE_AUTH_MOCK=true (ou absent) = mock ; =false = vrai backend.
const MOCK_MODE = import.meta.env.VITE_AUTH_MOCK !== 'false';

// Utilisateur factice renvoyé en mode mock.
// Reflète le MPD d'authentification : email + rôle (table role.libelle).
const MOCK_USER = {
  id: 1,
  email: 'demo@alimendo.app',
  role: 'membre',
};

// On réexporte getToken pour que le reste de l'app ait un point d'entrée unique
// ("tout ce qui touche à l'auth passe par auth.js") sans connaître token.js.
export { getToken };

/**
 * Connecte l'utilisateur.
 * @param {string} identifier - l'identifiant saisi. Le MPD utilise l'email comme identifiant.
 * @param {string} password
 * @returns {Promise<{ token: string, user: { id: number, email: string, role: string } }>}
 * @throws {Error} si les identifiants sont vides (mock) ou refusés (backend).
 */
export async function login(identifier, password) {
  if (MOCK_MODE) {
    // Simule la latence réseau, cohérent avec les setTimeout déjà utilisés ailleurs.
    await new Promise((resolve) => setTimeout(resolve, 400));

    if (!identifier || !password) {
      throw new Error('Identifiant et mot de passe requis.');
    }

    const token = 'mock.jwt.token';
    setToken(token);
    return { token, user: { ...MOCK_USER, email: identifier } };
  }

  // --- Mode réel : à activer quand FastAPI expose POST /auth/login ---------
  // Réponse attendue : { access_token: "...", user: { id, email, role } }
  const data = await api.post('/auth/login', { email: identifier, password });
  setToken(data.access_token);
  return { token: data.access_token, user: data.user };
}

/** Déconnecte l'utilisateur (supprime le token local). */
export function logout() {
  clearToken();
}

/**
 * Récupère l'utilisateur courant à partir du token stocké.
 * Utilisé au démarrage de l'app pour restaurer la session après un refresh.
 * @returns {Promise<{ id: number, email: string, role: string } | null>}
 */
export async function fetchCurrentUser() {
  const token = getToken();
  if (!token) return null;

  if (MOCK_MODE) {
    return MOCK_USER;
  }

  // --- Mode réel : route protégée FastAPI qui renvoie l'utilisateur du token.
  try {
    return await api.get('/auth/me');
  } catch {
    // Token invalide ou expiré → on nettoie pour éviter un état incohérent.
    clearToken();
    return null;
  }
}
