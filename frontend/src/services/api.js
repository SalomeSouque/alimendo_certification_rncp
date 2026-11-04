// src/services/api.js
// Thin wrapper around fetch. Single responsibility: talk to the FastAPI backend,
// attach the JWT when there is one, and turn HTTP errors into ApiError.
// No business logic here: only HTTP transport.

import { getToken, clearToken } from './token';

// Backend base URL. Read from .env (VITE_API_URL), never hard-coded elsewhere.
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

// Event fired on window when an authenticated call gets a 401
// (expired or revoked token). AuthProvider listens to it.
export const SESSION_EXPIRED_EVENT = 'alimendo:session-expired';

/** Error raised for any non-2xx response or network failure. */
export class ApiError extends Error {
  /**
   * @param {number} status - HTTP status, 0 when the server could not be reached.
   * @param {string} message - human-readable message (French, shown in the UI).
   * @param {any} [detail] - raw `detail` field returned by FastAPI.
   */
  constructor(status, message, detail) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Turns a FastAPI `detail` into a readable message.
 * 4xx business errors send a string; 422 validation errors send an array
 * of { loc, msg, type } objects.
 * @param {any} detail
 * @param {string} fallback
 * @returns {string}
 */
function messageFromDetail(detail, fallback) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => d.msg).filter(Boolean).join(' ') || fallback;
  }
  return fallback;
}

/**
 * Sends an HTTP request and returns the parsed JSON body.
 * @param {string} method - 'GET' | 'POST' | 'PUT' | 'DELETE'
 * @param {string} path - relative path, e.g. '/auth/login'
 * @param {object|FormData} [body] - JSON body, or FormData for file uploads
 * @returns {Promise<any>}
 * @throws {ApiError}
 */
async function request(method, path, body) {
  const headers = {};
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;

  // For FormData, the browser sets Content-Type itself, with the multipart
  // boundary. Setting it by hand would break the upload.
  if (body !== undefined && !isFormData) {
    headers['Content-Type'] = 'application/json';
  }

  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
    });
  } catch {
    // Network error, CORS refusal, backend down: fetch rejects without a response.
    throw new ApiError(0, 'Le serveur est injoignable. Vérifiez votre connexion puis réessayez.');
  }

  if (!res.ok) {
    let detail;
    try {
      detail = (await res.json()).detail;
    } catch {
      // Non-JSON body (proxy error page for instance): keep detail undefined.
    }

    // Central 401 handling. Only when a token was sent: a 401 on /auth/login
    // (wrong password) must not be treated as an expired session.
    if (res.status === 401 && token) {
      clearToken();
      window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
      throw new ApiError(401, 'Votre session a expiré. Reconnectez-vous pour continuer.', detail);
    }

    const fallback =
      res.status >= 500
        ? 'Le service est momentanément indisponible. Réessayez dans quelques instants.'
        : `Erreur ${res.status}`;
    throw new ApiError(res.status, messageFromDetail(detail, fallback), detail);
  }

  // 204 No Content: no body to parse.
  return res.status === 204 ? null : res.json();
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  put: (path, body) => request('PUT', path, body),
  del: (path) => request('DELETE', path),
};