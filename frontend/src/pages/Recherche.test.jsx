import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route } from 'react-router-dom';
import { renderWithProviders } from '../test/renderWithProviders';
import { mockFetch, jsonResponse } from '../test/mockFetch';
import Recherche from './Recherche';
import Analyser from './Analyser';

function renderAt(route) {
  return renderWithProviders(
    <Routes>
      <Route path="/analyser" element={<Analyser />} />
      <Route path="/recherche" element={<Recherche />} />
    </Routes>,
    { route },
  );
}

describe('Search (GET /search/aliments)', () => {
  it('Analyser form → /recherche → results linking to the food pages', async () => {
    const fetchMock = mockFetch(jsonResponse(200, {
      terme: 'saumon', nombre_resultats: 2,
      resultats: [
        { id_aliment: 26035, nom: 'Saumon, cru', source: 'CIQUAL', id_categorie: 4 },
        { id_aliment: 26036, nom: 'Saumon, fumé', source: 'CIQUAL', id_categorie: 4 },
      ],
    }));
    const user = userEvent.setup();
    renderAt('/analyser');

    await user.type(screen.getByLabelText('Rechercher un aliment par nom'), 'saumon');
    await user.click(screen.getByRole('button', { name: 'Rechercher' }));

    expect(await screen.findByRole('heading', { name: '2 résultats pour « saumon »' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Saumon, fumé' })).toHaveAttribute('href', '/aliment/26036');
    expect(new URL(fetchMock.mock.calls[0][0]).searchParams.get('q')).toBe('saumon');
  });

  it('no result: explains and suggests the barcode', async () => {
    mockFetch(jsonResponse(200, { terme: 'xyz', nombre_resultats: 0, resultats: [] }));
    renderAt('/recherche?q=xyzz');
    expect(await screen.findByRole('heading', { name: 'Aucun aliment trouvé pour « xyzz »' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'saisissez son code-barre' })).toBeInTheDocument();
  });

  it('server error: message in an alert', async () => {
    mockFetch(jsonResponse(500));
    renderAt('/recherche?q=saumon');
    expect(await screen.findByRole('alert')).toHaveTextContent(/momentanément indisponible/);
  });

  it('term shorter than 2 characters: no request, error on the field', async () => {
    const fetchMock = mockFetch();
    const user = userEvent.setup();
    renderAt('/analyser');

    await user.type(screen.getByLabelText('Rechercher un aliment par nom'), 's');
    await user.click(screen.getByRole('button', { name: 'Rechercher' }));

    expect(screen.getByLabelText('Rechercher un aliment par nom')).toHaveAccessibleDescription('Saisissez au moins 2 caractères.');
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
