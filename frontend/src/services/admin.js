// src/services/admin.js
// Admin endpoints (router backend/app/routers/admin.py), reserved to the admin role.
// Components never call fetch directly: they go through these functions.

import { api } from './api';

/** Role label returned by /auth/me for an admin account (ROLE_ADMIN backend side). */
export const ROLE_ADMIN = 'admin';

/**
 * @typedef {object} AdminAccount
 * @property {number} id
 * @property {string} email
 * @property {string} role
 * @property {string} created_at - ISO 8601 datetime
 * @property {boolean} acces_ia
 */

/**
 * @param {{ role?: string } | null} user
 * @returns {boolean} true when the user has the admin role.
 */
export function isAdmin(user) {
  return user?.role === ROLE_ADMIN;
}

/**
 * Lists the accounts, most recent first. GET /admin/utilisateurs.
 * @returns {Promise<AdminAccount[]>}
 * @throws {ApiError} 403 when the account is not (or no longer) an admin.
 */
export function listAccounts() {
  return api.get('/admin/utilisateurs');
}

/**
 * Opens or closes the AI access of an account. PATCH /admin/utilisateurs/{id}/acces-ia.
 * The backend reads acces_ia on every /ai/* call: the change applies immediately.
 * @param {number} id
 * @param {boolean} enabled
 * @returns {Promise<AdminAccount>} the updated account.
 * @throws {ApiError} 403 when not admin, 404 when the account no longer exists.
 */
export function setAiAccess(id, enabled) {
  return api.patch(`/admin/utilisateurs/${id}/acces-ia`, { acces_ia: enabled });
}
