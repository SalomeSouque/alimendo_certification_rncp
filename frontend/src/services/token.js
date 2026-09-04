// src/services/token.js
// Petit module dédié au stockage du token.
// Il existe pour éviter une dépendance circulaire entre api.js et auth.js :
// les deux ont besoin de lire le token, mais aucun ne doit dépendre de l'autre.
// Un seul endroit connaît la clé de stockage → un seul endroit à changer plus tard.

const TOKEN_KEY = 'alimendo_token';

/** @returns {string|null} le token JWT stocké, ou null s'il n'y en a pas. */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

/** @param {string} token */
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}
