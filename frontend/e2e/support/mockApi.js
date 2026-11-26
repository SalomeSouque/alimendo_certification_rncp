// e2e/support/mockApi.js
// Answers every backend call of the front with fixed data (shapes from docs/openapi.json).
// The data is deliberately "hard" for the layout: long CIQUAL / Open Food Facts names,
// full lists, long source titles. That is where mobile layouts usually break.

export const API_URL = 'http://api.e2e.test';

const TOKEN_KEY = 'alimendo_token'; // same key as src/services/token.js

const DISCLAIMER =
  'Score indicatif, basé sur le profil nutritionnel de l’aliment. Il ne constitue pas un avis médical et ne prédit pas l’effet de cet aliment sur vos symptômes.';

const food = (id, nom, extra = {}) => ({
  id_aliment: id, nom, source: 'CIQUAL', url_image: null, id_categorie: 4, ...extra,
});

const score = (niveau, libelle) => ({
  disponible: true, niveau, libelle, score_brut: niveau * 0.8, causes: [],
  completude: 0.9, parametres_utilises: 18, message: null, version_referentiel: 'v1',
});

function foodDetail(aliment) {
  return {
    aliment,
    score: score(-1, 'Modérément anti-inflammatoire'),
    badges: [
      { nutriment: 'omega3', niveau: 'riche', libelle: 'Riche en oméga-3', valeur: 2.1, unite: 'g' },
      { nutriment: 'magnesium', niveau: 'source', libelle: 'Source de magnésium', valeur: 30, unite: 'mg' },
      { nutriment: 'vitamine_d', niveau: 'riche', libelle: 'Riche en vitamine D', valeur: 8, unite: 'µg' },
      { nutriment: 'fer', niveau: 'aucun', libelle: null, valeur: 0.3, unite: 'mg' },
    ],
    alternatives: [
      { aliment: food(26050, 'Maquereau, filet, sans peau, cru'), score: score(-2, 'Fortement anti-inflammatoire') },
      { aliment: food(26069, 'Sardine, filets sans arêtes à l’huile d’olive, appertisés, égouttés'), score: score(-2, 'Fortement anti-inflammatoire') },
      { aliment: food(26043, 'Truite arc-en-ciel, élevage, crue'), score: score(-1, 'Modérément anti-inflammatoire') },
      { aliment: food(26101, 'Hareng fumé, à l’huile'), score: score(0, 'Neutre') },
    ],
    libelle_alternatives: 'Autres options au profil nutritionnel moins pro-inflammatoire',
    disclaimer: DISCLAIMER,
    mention_projet_etudiant: 'Projet étudiant à but pédagogique.',
    citation_source: 'Approche inspirée du Dietary Inflammatory Index (Shivappa et al., 2014).',
  };
}

const CIQUAL_FOOD = food(26035, 'Saumon atlantique, sauvage, cru', { url_image: '/assets/saumon.png' });
const OFF_PRODUCT = {
  id_aliment: null,
  nom: 'Sardines à l’huile d’olive vierge extra et au citron, pêchées en Atlantique Nord-Est',
  source: 'OFF',
  url_image: '/assets/sardine.png',
  id_categorie: null,
};

const SEARCH_RESULTS = [
  food(26035, 'Saumon atlantique, sauvage, cru'),
  food(26036, 'Saumon, élevage, cuit à la vapeur'),
  food(26037, 'Saumon fumé'),
  food(26038, 'Saumon, filet, sans peau, cuit au four, avec matière grasse ajoutée'),
  food(26039, 'Pavé de saumon à l’oseille et pommes de terre vapeur, plat cuisiné, préemballé, cuit'),
  food(26040, 'Rillettes de saumon'),
];

const CHAT_ANSWER = {
  reponse:
    'Les études disponibles associent une alimentation riche en oméga-3 à un profil moins inflammatoire. Elles restent peu nombreuses et portent sur de petits effectifs.\n\nLes sources ci-dessous détaillent ces résultats. Pour adapter votre alimentation, parlez-en à un professionnel de santé.',
  intention: 'in_scope',
  action: 'RAG_RETRIEVAL',
  sources: [
    { id_source: 's1', titre: 'Dietary factors and endometriosis: a systematic review of observational studies (2023)', url: 'https://example.org/etude-longue-url-pour-tester-le-retour-a-la-ligne' },
    { id_source: 's2', titre: 'EndoFrance — Alimentation et endométriose', url: 'https://example.org/endofrance' },
  ],
  disclaimer: 'Information générale, ne remplace pas un avis médical.',
};

/**
 * Starts the fake backend for one page.
 * @param {import('@playwright/test').Page} page
 * @param {{ auth?: boolean, aiAccess?: boolean, vision?: 'recognised'|'notFound'|'slow' }} [options]
 *   auth: a JWT is stored and /auth/me returns a user;
 *   aiAccess: false makes /ai/* answer 403 (account waiting for validation);
 *   vision: answer of the photo analysis ('slow' never answers: "identification en cours").
 */
export async function mockApi(page, { auth = false, aiAccess = true, vision = 'recognised' } = {}) {
  if (auth) {
    await page.addInitScript((key) => localStorage.setItem(key, 'e2e.jwt.token'), TOKEN_KEY);
  }

  const user = { id: 7, email: 'lea.dupont@exemple.fr', role: 'user', acces_ia: aiAccess };

  await page.route(`${API_URL}/**`, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const json = (body, status = 200) => route.fulfill({ status, json: body });

    if (path === '/auth/me') return auth ? json(user) : json({ detail: 'Non authentifié' }, 401);
    if (path === '/search/categories') return json([{ id_categorie: 4, nom: 'Poissons et produits de la mer', image: null }]);
    if (path === '/search/aliments') {
      const q = url.searchParams.get('q') ?? '';
      const resultats = q.toLowerCase().startsWith('saumon') ? SEARCH_RESULTS : [];
      return json({ terme: q, nombre_resultats: resultats.length, resultats });
    }
    if (path.startsWith('/score/aliment/')) return json(foodDetail(CIQUAL_FOOD));
    if (path.startsWith('/score/code-barre/')) return json(foodDetail(OFF_PRODUCT));

    if (path.startsWith('/ai/')) {
      if (!aiAccess) return json({ detail: 'Accès aux outils IA en attente de validation.' }, 403);
      if (path === '/ai/chat') return json(CHAT_ANSWER);
      if (path === '/ai/vision') {
        if (vision === 'slow') return new Promise(() => {}); // the page stays on "Identification en cours…"
        if (vision === 'notFound') {
          return json({ statut: 'non_reconnu', label_identifie: null, resultat: null, message: 'La photo n’a pas permis d’identifier l’aliment.' });
        }
        return json({ statut: 'reconnu', label_identifie: 'saumon', resultat: foodDetail(CIQUAL_FOOD), message: null });
      }
    }
    return json({ detail: `Route non simulée : ${path}` }, 404);
  });
}
