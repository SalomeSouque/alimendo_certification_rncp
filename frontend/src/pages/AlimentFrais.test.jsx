import { screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route } from 'react-router-dom';
import { renderWithProviders } from '../test/renderWithProviders';
import { mockFetch, jsonResponse } from '../test/mockFetch';
import { foodDetail } from '../test/fixtures';
import AlimentFrais from './AlimentFrais';

const photo = (type = 'image/jpeg', size = 2000) => new File([new Uint8Array(size)], 'pomme.jpg', { type });
const fileInput = () => document.querySelector('input[type="file"]');

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/aliment-frais" element={<AlimentFrais />} />
      <Route path="/connexion" element={<p>Page connexion</p>} />
    </Routes>,
    { route: '/aliment-frais' },
  );
}

beforeEach(() => {
  // jsdom has no object URLs.
  URL.createObjectURL = vi.fn(() => 'blob:preview');
  URL.revokeObjectURL = vi.fn();
});

describe('Fresh food photo (POST /ai/vision)', () => {
  it('recognised: loading state, then the identified label and the score with a h2 title', async () => {
    let resolve;
    mockFetch(() => new Promise((r) => { resolve = r; }));
    const user = userEvent.setup();
    renderPage();

    await user.upload(fileInput(), photo());
    expect(screen.getByRole('status')).toHaveTextContent('Identification en cours');
    expect(screen.getByRole('img', { name: 'Photo envoyée' })).toBeInTheDocument();

    resolve(jsonResponse(200, {
      statut: 'reconnu', contenu: 'aliment_unique', label_identifie: 'saumon', score_confiance: 0.9,
      id_aliment: 26035, resultat: foodDetail(), message: null,
    }));

    expect(await screen.findByText('saumon')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Saumon, cru' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Aliment frais' })).toBeInTheDocument();
    expect(screen.getByText(/Score indicatif/)).toBeInTheDocument();
  });

  it('not matched: shows the API message, retry brings the drop zone back', async () => {
    mockFetch(jsonResponse(200, {
      statut: 'non_rapproche', label_identifie: 'durian', resultat: null,
      message: '« durian » a été reconnu, mais cet aliment n’est pas dans notre base. Essayez la recherche par nom.',
    }));
    const user = userEvent.setup();
    renderPage();

    await user.upload(fileInput(), photo());

    expect(await screen.findByRole('heading', { name: 'Aliment non reconnu' })).toBeInTheDocument();
    expect(screen.getByText(/« durian » a été reconnu/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Réessayer avec une photo' }));
    expect(screen.getByText('Déposer une photo de l\'aliment')).toBeInTheDocument();
  });

  it('503: service unavailable message in an alert', async () => {
    mockFetch(jsonResponse(503, { detail: 'Le service de reconnaissance photo est temporairement indisponible, essayez la recherche textuelle.' }));
    const user = userEvent.setup();
    renderPage();

    await user.upload(fileInput(), photo('image/png'));

    expect(await screen.findByRole('alert')).toHaveTextContent('temporairement indisponible');
    expect(screen.getByRole('link', { name: 'Rechercher par nom' })).toHaveAttribute('href', '/analyser');
  });

  it('server-side refusal (413): API message shown', async () => {
    mockFetch(jsonResponse(413, { detail: 'Image trop volumineuse (5 Mo maximum).' }));
    const user = userEvent.setup();
    renderPage();
    await user.upload(fileInput(), photo());
    expect(await screen.findByRole('alert')).toHaveTextContent('Image trop volumineuse (5 Mo maximum).');
  });

  it('wrong format or too large: refused before any upload', async () => {
    const fetchMock = mockFetch();
    renderPage();

    // fireEvent: userEvent.upload would filter the file through the accept attribute.
    fireEvent.change(fileInput(), { target: { files: [photo('image/gif')] } });
    expect(screen.getByRole('alert')).toHaveTextContent('JPEG, PNG ou WebP');
    fireEvent.change(fileInput(), { target: { files: [photo('image/jpeg', 6 * 1024 * 1024)] } });
    expect(screen.getByRole('alert')).toHaveTextContent('5 Mo maximum');
    expect(fileInput()).toHaveAttribute('aria-invalid', 'true');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('drag and drop: a dropped photo is analysed', async () => {
    const fetchMock = mockFetch(jsonResponse(200, { statut: 'echec', resultat: null, message: 'Aucun aliment n’a été reconnu sur cette photo.' }));
    renderPage();

    fireEvent.drop(screen.getByText('Déposer une photo de l\'aliment').closest('label'), {
      dataTransfer: { files: [photo()] },
    });

    expect(await screen.findByText('Aucun aliment n’a été reconnu sur cette photo.')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('401 (expired session): redirected to the login page', async () => {
    localStorage.setItem('alimendo_token', 'soon-expired');
    mockFetch(
      jsonResponse(200, { id: 7, email: 'lea@example.com', role: 'user' }),
      jsonResponse(401, { detail: 'Jeton absent, invalide ou expiré.' }),
    );
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole('button', { name: 'Se déconnecter' });

    await user.upload(fileInput(), photo());

    expect(await screen.findByText('Page connexion')).toBeInTheDocument();
  });

  it('403: shows the pending access card', async () => {
    mockFetch(jsonResponse(403, { detail: 'Accès en attente de validation.' }));
    const user = userEvent.setup();
    renderPage();

    await user.upload(fileInput(), photo());

    expect(await screen.findByRole('heading', { name: 'Accès en attente de validation' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Rechercher un aliment' })).toHaveAttribute('href', '/analyser');
  });
});