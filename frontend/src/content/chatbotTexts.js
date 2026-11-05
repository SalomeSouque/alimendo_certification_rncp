// src/content/chatbotTexts.js
// Fixed chatbot texts shown by the frontend. They are copied word for word
// from RAG_medical-guidelines.md (guidelines-v1.0-2026-09), section 7, and must
// never be rewritten here. The answers and their short disclaimer (§7.8) come
// from the API.

/** §7.7 — long disclaimer: permanent banner and first opening. */
export const CHATBOT_LONG_DISCLAIMER = {
  title: 'Projet étudiant / prototype de démonstration.',
  lines: [
    'Cet assistant répond uniquement à partir d’un petit ensemble de documents sélectionnés. Il ne consulte pas Internet et n’utilise pas de connaissances médicales au-delà de ces documents.',
    'Il ne pose aucun diagnostic, ne recommande aucun traitement et ne remplace en aucun cas l’avis d’un professionnel de santé.',
    'À ce jour, les recommandations internationales ne permettent de conseiller aucun régime alimentaire spécifique dans l’endométriose.',
  ],
};

// Privacy notice under the input (GDPR, not a medical text).
// Questions are not stored; in-scope ones are sent to Mistral AI to generate
// the answer. Documented in docs/rgpd/README.md.
export const CHATBOT_PRIVACY_NOTICE =
  'N’indiquez pas d’informations personnelles ou de santé. Vos questions ne sont pas enregistrées, mais peuvent être transmises à un service d’IA externe (Mistral AI) pour générer la réponse.';
