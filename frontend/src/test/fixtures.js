// src/test/fixtures.js
// API payloads shaped like docs/openapi.json (AlimentDetail, RechercheResultat).

const DISCLAIMER =
  'Score indicatif, basé sur le profil nutritionnel de l’aliment. Il ne constitue pas un avis médical et ne prédit pas l’effet de cet aliment sur vos symptômes.';

export function foodDetail(overrides = {}) {
  return {
    aliment: { id_aliment: 26035, nom: 'Saumon, cru', source: 'CIQUAL', url_image: null, id_categorie: 4 },
    score: {
      disponible: true, niveau: -1, libelle: 'Modérément anti-inflammatoire', score_brut: -0.8,
      causes: [], completude: 0.9, parametres_utilises: 18, message: null, version_referentiel: 'v1',
    },
    badges: [
      { nutriment: 'fer', niveau: 'aucun', libelle: null, valeur: 0.3, unite: 'mg' },
      { nutriment: 'magnesium', niveau: 'source', libelle: 'Source de magnésium', valeur: 30, unite: 'mg' },
    ],
    alternatives: [
      {
        aliment: { id_aliment: 26050, nom: 'Maquereau, cru', source: 'CIQUAL', url_image: null, id_categorie: 4 },
        score: { disponible: true, niveau: -2, libelle: 'Fortement anti-inflammatoire', causes: [], completude: 1, parametres_utilises: 18, version_referentiel: 'v1' },
      },
    ],
    libelle_alternatives: 'Autres options au profil nutritionnel moins pro-inflammatoire',
    disclaimer: DISCLAIMER,
    mention_projet_etudiant: 'Projet étudiant à but pédagogique.',
    citation_source: 'Approche inspirée du Dietary Inflammatory Index (Shivappa et al., 2014).',
    ...overrides,
  };
}

export const CATEGORIES = [{ id_categorie: 4, nom: 'Poissons', image: null }];

// Accounts as returned by GET /admin/utilisateurs (UtilisateurAdmin), most recent first.
export const ADMIN_USER = { id: 1, email: 'admin@alimendo.fr', role: 'admin', acces_ia: true };

export function adminAccounts() {
  return [
    { id: 12, email: 'camille.martin@exemple.fr', role: 'user', created_at: '2026-11-08T10:00:00Z', acces_ia: false },
    { id: 11, email: 'jury.simplon@exemple.fr', role: 'user', created_at: '2026-11-06T10:00:00Z', acces_ia: false },
    { id: 9, email: 'sophie.l@exemple.fr', role: 'user', created_at: '2026-10-28T10:00:00Z', acces_ia: true },
    { id: 1, email: 'admin@alimendo.fr', role: 'admin', created_at: '2026-09-14T10:00:00Z', acces_ia: true },
  ];
}
