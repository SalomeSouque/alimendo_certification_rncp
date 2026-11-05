// src/services/chat.js
// Chatbot service: the only place that knows the /ai/chat contract.

import { api } from './api';

// Mirrors ChatRequest (backend): 3 to 1000 characters.
export const QUESTION_MIN_LENGTH = 3;
export const QUESTION_MAX_LENGTH = 1000;

// Router action that sends the user to the food scan / search (§7.2).
export const ACTION_REDIRECT_SCAN = 'REDIRECT_SCAN';

/**
 * @typedef {object} ChatSource
 * @property {string} id_source
 * @property {string} titre
 * @property {string|null} [url]
 *
 * @typedef {object} ChatAnswer
 * @property {string} reponse - answer text, paragraphs separated by blank lines
 * @property {string} intention - router class (in_scope, out_of_scope…)
 * @property {string} action - router action (RAG_RETRIEVAL, REDIRECT_SCAN…)
 * @property {ChatSource[]} sources - cited documents, possibly empty
 * @property {string|null} disclaimer - short disclaimer, null for §7.5 / §7.6
 */

/**
 * Sends a question to the chatbot. POST /ai/chat (JWT required).
 * @param {string} question
 * @returns {Promise<ChatAnswer>}
 * @throws {ApiError} 401 (handled centrally), 422, 503 when an AI service is down.
 */
export async function askChatbot(question) {
  const data = await api.post('/ai/chat', { question: question.trim() });
  return {
    ...data,
    // One entry per document: several chunks of the same source can be cited.
    sources: dedupeSources(data.sources ?? []),
    disclaimer: data.disclaimer ?? null,
  };
}

/**
 * @param {ChatSource[]} sources
 * @returns {ChatSource[]}
 */
function dedupeSources(sources) {
  const seen = new Set();
  return sources.filter((s) => {
    if (seen.has(s.id_source)) return false;
    seen.add(s.id_source);
    return true;
  });
}
