// src/services/api.js
// Wrapper minimal autour de fetch. Rôle unique : parler au backend FastAPI
// en attachant automatiquement le token JWT quand il existe.
// Aucune logique métier ici — juste le transport HTTP.

import { getToken } from './token';

// URL de base du backend. Externalisée dans .env (jamais en dur ailleurs).
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

/**
 * Effectue une requête HTTP et renvoie le JSON de la réponse.
 * @param {string} method - 'GET' | 'POST' | 'PUT' | 'DELETE'
 * @param {string} path - chemin relatif, ex. '/auth/login'
 * @param {object} [body] - corps JSON pour POST/PUT
 * @returns {Promise<any>}
 * @throws {Error} si la réponse HTTP n'est pas 2xx
 */
async function request(method, path, body) {
  const headers = { 'Content-Type': 'application/json' };

  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    // On tente d'extraire le message d'erreur renvoyé par FastAPI ({ detail: "..." }).
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail ?? detail;
    } catch {
      // Réponse non-JSON : on garde le statusText.
    }
    throw new Error(`API ${res.status} — ${detail}`);
  }

  // 204 No Content → pas de corps à parser.
  return res.status === 204 ? null : res.json();
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  put: (path, body) => request('PUT', path, body),
  del: (path) => request('DELETE', path),
};
