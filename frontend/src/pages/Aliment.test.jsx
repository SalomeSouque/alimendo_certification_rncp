import { screen, within, fireEvent } from '@testing-library/react';
import { Routes, Route } from 'react-router-dom';
import { renderWithProviders } from '../test/renderWithProviders';
import { mockFetch, jsonResponse } from '../test/mockFetch';
import { foodDetail, CATEGORIES } from '../test/fixtures';
import { resetCategoriesCache } from '../services/score';
import Aliment from './Aliment';

function renderAt(route) {
  return renderWithProviders(
    <Routes>
      <Route path="/aliment/:id" element={<Aliment />} />
      <Route path="/produit/:code" element={<Aliment />} />
    </Routes>,
    { route },
  );
}

beforeEach(() => resetCategoriesCache());

describe('Food page (GET /score/aliment/{id})', () => {
  it('success: name, category, score label, validated badges, disclaimers and alternatives', async () => {
    const fetchMock = mockFetch(jsonResponse(200, foodDetail()), jsonResponse(200, CATEGORIES));
    renderAt('/aliment/26035');

    expect(screen.getByRole('status')).toHaveTextContent('Chargement du score');
    expect(await screen.findByRole('heading', { level: 1, name: 'Saumon, cru' })).toBeInTheDocument();
    expect(screen.getByText('Poissons')).toBeInTheDocument();
    expect(screen.getAllByRole('img', { name: 'Potentiel inflammatoire estimé : Modérément anti-inflammatoire' })).toHaveLength(1);
    // Only badges with a validated label are displayed.
    expect(screen.getByText('Source de magnésium')).toBeInTheDocument();
    expect(screen.queryByText(/fer/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Score indicatif/)).toBeInTheDocument();
    expect(screen.getByText(/Shivappa et al\., 2014/)).toBeInTheDocument();

    const alternatives = screen.getByRole('region', { name: 'Autres options au profil nutritionnel moins pro-inflammatoire' });
    expect(within(alternatives).getByRole('link', { name: /Maquereau, cru/ })).toHaveAttribute('href', '/aliment/26050');
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/score\/aliment\/26035$/);
  });

  it('score unavailable: shows the API message instead of the bar', async () => {
    const detail = foodDetail({
      score: { disponible: false, niveau: null, libelle: null, causes: ['completude'], completude: 0.2, parametres_utilises: 3, version_referentiel: 'v1',
        message: 'Score indisponible : données nutritionnelles insuffisantes pour cet aliment.' },
      alternatives: [],
    });
    mockFetch(jsonResponse(200, detail), jsonResponse(200, CATEGORIES));
    renderAt('/aliment/1');

    expect(await screen.findByText('Score indisponible : données nutritionnelles insuffisantes pour cet aliment.')).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: /Potentiel inflammatoire/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('region')).not.toBeInTheDocument();
  });

  it('categories unavailable: the score is still displayed', async () => {
    mockFetch(jsonResponse(200, foodDetail()), jsonResponse(500));
    renderAt('/aliment/26035');
    expect(await screen.findByRole('heading', { level: 1, name: 'Saumon, cru' })).toBeInTheDocument();
  });

  it('404: "food not found" state', async () => {
    mockFetch(jsonResponse(404, { detail: 'Aliment introuvable.' }));
    renderAt('/aliment/999999');
    expect(await screen.findByRole('alert')).toHaveTextContent('Cet aliment est introuvable.');
  });

  it('server error: generic unavailable message', async () => {
    mockFetch(jsonResponse(500));
    renderAt('/aliment/26035');
    expect(await screen.findByRole('alert')).toHaveTextContent(/momentanément indisponible/);
  });
});

describe('Product page (GET /score/code-barre/{code})', () => {
  it('success: Open Food Facts product, "Produit emballé" kicker, no category call', async () => {
    const detail = foodDetail({
      aliment: { id_aliment: null, nom: 'Pâte à tartiner', source: 'OFF', url_image: 'https://images.openfoodfacts.org/x.jpg', id_categorie: null },
      alternatives: [],
    });
    const fetchMock = mockFetch(jsonResponse(200, detail));
    renderAt('/produit/3017620422003');

    expect(await screen.findByRole('heading', { level: 1, name: 'Pâte à tartiner' })).toBeInTheDocument();
    expect(screen.getByText('Produit emballé')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/score\/code-barre\/3017620422003$/);
  });

  it('404: unknown barcode message', async () => {
    mockFetch(jsonResponse(404, { detail: 'Produit inconnu d’Open Food Facts.' }));
    renderAt('/produit/00000000');
    expect(await screen.findByRole('alert')).toHaveTextContent('Ce code-barre est inconnu d’Open Food Facts');
  });

  it('503: Open Food Facts unreachable, API message shown', async () => {
    mockFetch(jsonResponse(503, { detail: 'Open Food Facts est momentanément injoignable.' }));
    renderAt('/produit/3017620422003');
    expect(await screen.findByRole('alert')).toHaveTextContent('Open Food Facts est momentanément injoignable.');
  });
});

describe('Product image', () => {
  it('broken Open Food Facts image: falls back to the pictogram', async () => {
    const detail = foodDetail({
      aliment: { id_aliment: null, nom: 'Biscuit', source: 'OFF', url_image: 'https://images.openfoodfacts.org/broken.jpg', id_categorie: null },
      alternatives: [],
    });
    mockFetch(jsonResponse(200, detail));
    const { container } = renderAt('/produit/3017620422003');
    await screen.findByRole('heading', { level: 1, name: 'Biscuit' });

    const img = container.querySelector('.food-img');
    expect(img).toHaveAttribute('src', 'https://images.openfoodfacts.org/broken.jpg');
    fireEvent.error(img);
    expect(container.querySelector('.food-img')).toHaveAttribute('src', '/assets/couvert.svg');
  });
});