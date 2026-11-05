// src/services/auth.js
// Authentication service: the single entry point for "being logged in".
// Components never call fetch or localStorage for auth: they go through here
// (via AuthProvider).

import { api } from './api';
import { getToken, setToken, clearToken } from './token';

// Mock mode is now opt-in: only VITE_AUTH_MOCK=true enables it.
// Absent or any other value = real backend. This matters for the Docker build,
// where frontend/.env is not always present at build time.
const MOCK_MODE = import.meta.env.VITE_AUTH_MOCK === 'true';

// Minimum password length, mirrors RegisterRequest (backend, OWASP A07).
export const PASSWORD_MIN_LENGTH = 8;

const MOCK_USER = { id: 1, email: 'demo@alimendo.app', role: 'user' };

export { getToken };

/**
 * Stores the token from a TokenResponse and returns the session.
 * @param {{ access_token: string, user: { id: number, email: string, role: string } }} data
 */
function openSession(data) {
  setToken(data.access_token);
  return { token: data.access_token, user: data.user };
}

/**
 * Logs the user in. POST /auth/login → TokenResponse.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{ token: string, user: { id: number, email: string, role: string } }>}
 * @throws {ApiError} 401 on wrong credentials, 422 on invalid payload.
 */
export async function login(email, password) {
  if (MOCK_MODE) {
    await new Promise((resolve) => setTimeout(resolve, 400));
    if (!email || !password) throw new Error('Email et mot de passe requis.');
    setToken('mock.jwt.token');
    return { token: 'mock.jwt.token', user: { ...MOCK_USER, email } };
  }
  const data = await api.post('/auth/login', { email: email.trim(), password });
  return openSession(data);
}

/**
 * Creates an account and logs the user in. POST /auth/register → TokenResponse (201).
 * @param {string} email
 * @param {string} password - at least PASSWORD_MIN_LENGTH characters.
 * @param {boolean} consent - explicit consent (GDPR art. 9.2.a), must be true.
 * @throws {ApiError} 409 if the email is taken, 422 on invalid payload.
 */
export async function register(email, password, consent) {
  if (MOCK_MODE) {
    return login(email, password);
  }
  const data = await api.post('/auth/register', {
    email: email.trim(),
    password,
    consentement: consent,
  });
  return openSession(data);
}

/** Logs the user out (removes the local token). */
export function logout() {
  clearToken();
}

/**
 * Returns the current user from the stored token, or null.
 * Called on app start to restore the session after a page reload.
 * GET /auth/me: a 401 means the token expired, api.js already cleared it.
 * @returns {Promise<{ id: number, email: string, role: string } | null>}
 */
export async function fetchCurrentUser() {
  if (!getToken()) return null;
  if (MOCK_MODE) return MOCK_USER;
  try {
    return await api.get('/auth/me');
  } catch {
    // Expired token or backend down: start logged out rather than stuck.
    clearToken();
    return null;
  }
}