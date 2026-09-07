// src/config/features.js
// Source de vérité UNIQUE du "mur de connexion".
//
// Pour rendre une feature publique : retire sa clé de ce tableau.
// Pour en protéger une nouvelle : ajoute sa clé.
// AuthGate lit cette liste → aucune autre modification nécessaire ailleurs.
//
// Décision actuelle : seules les 2 features IA (coûteuses / personnalisées)
// sont derrière le mur. Le scan code-barre et la recherche par nom restent publics.
export const PROTECTED_FEATURES = [
  'aliment-frais', // reconnaissance d'aliment par photo (VLM Qwen)
  'chatbot',       // chatbot RAG (LangChain/LlamaIndex)
];

/**
 * @param {string} feature
 * @returns {boolean} true si la feature nécessite un compte.
 */
export function isFeatureProtected(feature) {
  return PROTECTED_FEATURES.includes(feature);
}
