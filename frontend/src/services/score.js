// src/services/score.js
// Food data service: search, categories and scores (public endpoints).

import { api } from './api';

export const SEARCH_MIN_LENGTH = 2;
export const SEARCH_MAX_LENGTH = 100;
// EAN barcode: 8 to 14 digits, same pattern as the backend.
export const BARCODE_PATTERN = /^\d{8,14}$/;

/**
 * Searches foods by name. GET /search/aliments?q=&limite=
 * @param {string} term - 2 to 100 characters
 * @param {number} [limit=20] - 1 to 50
 * @returns {Promise<{ terme: string, nombre_resultats: number, resultats: object[] }>}
 */
export function searchFoods(term, limit = 20) {
  const params = new URLSearchParams({ q: term.trim(), limite: String(limit) });
  return api.get(`/search/aliments?${params}`);
}

/** Lists food categories. GET /search/categories */
export function getCategories() {
  return api.get('/search/categories');
}

/**
 * Score, badges and alternatives of a CIQUAL food. GET /score/aliment/{id}
 * @param {number|string} id
 * @returns {Promise<object>} AlimentDetail
 * @throws {ApiError} 404 when the food does not exist.
 */
export function getFoodScore(id) {
  return api.get(`/score/aliment/${encodeURIComponent(id)}`);
}

/**
 * Score of a packaged product from its barcode. GET /score/code-barre/{code}
 * @param {string} code - 8 to 14 digits
 * @returns {Promise<object>} AlimentDetail
 * @throws {Error} before any request when the code is malformed.
 * @throws {ApiError} 404 unknown product, 503 Open Food Facts unreachable.
 */
export function getBarcodeScore(code) {
  const clean = String(code).replace(/\s/g, '');
  if (!BARCODE_PATTERN.test(clean)) {
    return Promise.reject(new Error('Le code-barre doit contenir entre 8 et 14 chiffres.'));
  }
  return api.get(`/score/code-barre/${clean}`);
}
