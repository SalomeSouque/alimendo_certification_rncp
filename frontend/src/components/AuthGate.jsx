// src/components/AuthGate.jsx
// Garde d'accès qui s'ajoute "PAR-DESSUS" une page, sans la réécrire.
//
// Logique :
//   1. Si la feature n'est pas dans la liste protégée → passe-plat (rend le contenu).
//      => retirer une clé de config/features.js suffit à ouvrir la feature.
//   2. Si on est encore en train de vérifier le token → on n'affiche rien (évite un flash).
//   3. Si protégée ET non connecté → on affiche l'état "connexion requise"
//      À LA PLACE de l'action (pas de redirection).
//   4. Sinon → contenu normal.
//
// Usage au niveau des routes (recommandé, zéro modif dans les pages) :
//   <Route path="/chatbot" element={<AuthGate feature="chatbot"><Chatbot /></AuthGate>} />

import { useAuth } from '../context/AuthContext';
import { isFeatureProtected } from '../config/features';
import LoginRequired from './LoginRequired';

export default function AuthGate({ feature, children }) {
  const { isAuthenticated, loading } = useAuth();

  if (feature && !isFeatureProtected(feature)) return children;
  if (loading) return null;
  if (!isAuthenticated) return <LoginRequired feature={feature} />;
  return children;
}
