import { searchFoods, getCategories, getFoodScore, getBarcodeScore } from './score';
import { mockFetch, jsonResponse } from '../test/mockFetch';

describe('score.js (public endpoints)', () => {
  it('searchFoods: encodes the term and sends the limit', async () => {
    const fetchMock = mockFetch(jsonResponse(200, { terme: 'pâte', nombre_resultats: 0, resultats: [] }));
    await searchFoods(' pâtes & riz ', 10);
    const url = new URL(fetchMock.mock.calls[0][0]);
    expect(url.pathname).toBe('/search/aliments');
    expect(url.searchParams.get('q')).toBe('pâtes & riz');
    expect(url.searchParams.get('limite')).toBe('10');
  });

  it('getCategories: GET /search/categories', async () => {
    const fetchMock = mockFetch(jsonResponse(200, [{ id_categorie: 1, nom: 'Poissons' }]));
    await expect(getCategories()).resolves.toHaveLength(1);
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/search\/categories$/);
  });

  it('getFoodScore: 404 becomes an ApiError with the API message', async () => {
    mockFetch(jsonResponse(404, { detail: 'Aliment introuvable.' }));
    await expect(getFoodScore(999)).rejects.toMatchObject({ status: 404, message: 'Aliment introuvable.' });
  });

  it('getBarcodeScore: rejects a malformed code without calling the API', async () => {
    const fetchMock = mockFetch();
    await expect(getBarcodeScore('12AB')).rejects.toThrow('entre 8 et 14 chiffres');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('getBarcodeScore: strips spaces, 503 when Open Food Facts is down', async () => {
    const fetchMock = mockFetch(jsonResponse(503, { detail: 'Open Food Facts est injoignable.' }));
    await expect(getBarcodeScore('3 017620 422003')).rejects.toMatchObject({ status: 503 });
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/score\/code-barre\/3017620422003$/);
  });
});
