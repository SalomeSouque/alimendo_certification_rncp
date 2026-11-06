// src/services/vision.js
// Photo recognition service: POST /ai/vision (multipart, field "image", JWT).

import { api } from './api';

// Same limits as the backend (routers/ai.py): checked before the upload
// so the user does not wait for a request that will be refused.
export const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
export const MAX_IMAGE_SIZE = 5 * 1024 * 1024; // 5 MB

// The backend gives Ollama 30 s (OLLAMA_TIMEOUT_SECONDS); keep a margin for
// the upload and the score computation before giving up on the client side.
export const VISION_TIMEOUT_MS = 45_000;

// VisionResponse.statut
export const VISION_STATUS = { RECOGNIZED: 'reconnu', NOT_MATCHED: 'non_rapproche', FAILED: 'echec' };

/**
 * Checks a file before upload.
 * @param {File|null|undefined} file
 * @returns {string|null} error message, or null when the file can be sent.
 */
export function validateImage(file) {
  if (!file) return 'Choisissez une photo.';
  if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
    return 'Format non pris en charge. Utilisez une photo JPEG, PNG ou WebP.';
  }
  if (file.size > MAX_IMAGE_SIZE) {
    return 'Photo trop lourde (5 Mo maximum). Réduisez-la ou prenez-en une autre.';
  }
  return null;
}

/**
 * Sends a photo to the VLM and returns the recognition result.
 * @param {File} file - already checked with validateImage
 * @returns {Promise<object>} VisionResponse: statut, label_identifie, resultat (AlimentDetail) or message
 * @throws {ApiError} 401 (handled centrally), 413, 415, 422, 503, or 0 on timeout.
 */
export function identifyFood(file) {
  const form = new FormData();
  form.append('image', file, file.name);
  return api.post('/ai/vision', form, { timeoutMs: VISION_TIMEOUT_MS });
}
