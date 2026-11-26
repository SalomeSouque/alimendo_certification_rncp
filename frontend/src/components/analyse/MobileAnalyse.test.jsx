// Full-screen analysis on phones (maquettes M3): tabs, barcode, photo, "Écrire".
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route, useParams } from 'react-router-dom';
import { renderWithProviders } from '../../test/renderWithProviders';
import { mockFetch, jsonResponse } from '../../test/mockFetch';
import { mockViewport } from '../../test/viewport';
import { foodDetail } from '../../test/fixtures';
import * as barcode from '../../services/barcode';
import Analyser from '../../pages/Analyser';
import ProduitEmballe from '../../pages/ProduitEmballe';
import AlimentFrais from '../../pages/AlimentFrais';
import Recherche from '../../pages/Recherche';

vi.mock('../../services/barcode', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    isCameraSupported: vi.fn(() => true),
    decodeBarcodeFromFile: vi.fn(),
    startCameraScan: vi.fn(() => new Promise(() => {})), // camera "opening"
  };
});

function ProductStub() {
  return <p>Produit {useParams().code}</p>;
}

function renderApp(route) {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<p>Page accueil</p>} />
      <Route path="/analyser" element={<Analyser />} />
      <Route path="/produit-emballe" element={<ProduitEmballe />} />
      <Route path="/aliment-frais" element={<AlimentFrais />} />
      <Route path="/recherche" element={<Recherche />} />
      <Route path="/produit/:code" element={<ProductStub />} />
    </Routes>,
    { route },
  );
}

const photo = () => new File([new Uint8Array(10)], 'photo.jpg', { type: 'image/jpeg' });

beforeEach(() => {
  vi.clearAllMocks();
  mockViewport(360);
  barcode.isCameraSupported.mockReturnValue(true);
  barcode.startCameraScan.mockImplementation(() => new Promise(() => {}));
});

describe('Phone: full-screen analysis with bottom tabs', () => {
  it('"Analyser un aliment" opens the Code-barre tab directly', async () => {
    renderApp('/analyser');
    expect(await screen.findByRole('heading', { name: 'Scanner un code-barre' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Code-barre' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Photo' })).toHaveAttribute('href', '/aliment-frais');
    expect(screen.getByRole('link', { name: 'Écrire' })).toHaveAttribute('href', '/recherche');
  });

  it('Code-barre: the camera starts on its own, no site header or "?" bubble', async () => {
    renderApp('/produit-emballe');
    await waitFor(() => expect(barcode.startCameraScan).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('status')).toHaveTextContent('Ouverture de la caméra');
    expect(screen.getByLabelText('Importer une photo du code-barre')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Une question/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Ouvrir le menu' })).not.toBeInTheDocument();
  });

  it('Code-barre: a readable photo opens the product', async () => {
    barcode.decodeBarcodeFromFile.mockResolvedValue('3017620422003');
    const user = userEvent.setup();
    renderApp('/produit-emballe');
    await user.upload(screen.getByLabelText('Importer une photo du code-barre'), photo());
    expect(await screen.findByText('Produit 3017620422003')).toBeInTheDocument();
  });

  it('Code-barre without camera: explanation, import still available', () => {
    barcode.isCameraSupported.mockReturnValue(false);
    renderApp('/produit-emballe');
    expect(screen.getByText(/caméra n’est pas disponible/)).toBeInTheDocument();
    expect(screen.getByLabelText('Importer une photo du code-barre')).toBeInTheDocument();
    expect(barcode.startCameraScan).not.toHaveBeenCalled();
  });

  it('✕ leaves the analysis for the home page', async () => {
    const user = userEvent.setup();
    renderApp('/produit-emballe');
    await user.click(screen.getByRole('button', { name: 'Quitter l’analyse' }));
    expect(screen.getByText('Page accueil')).toBeInTheDocument();
  });

  it('Photo: the shutter opens the phone camera (capture="environment")', () => {
    renderApp('/aliment-frais');
    expect(screen.getByLabelText('Prendre une photo de l’aliment')).toHaveAttribute('capture', 'environment');
    expect(screen.getByLabelText('Importer une photo de l’aliment')).not.toHaveAttribute('capture');
    expect(screen.getByRole('link', { name: 'Photo' })).toHaveAttribute('aria-current', 'page');
  });

  it('Photo: loading in the site layout, then the result', async () => {
    let answer;
    mockFetch(() => new Promise((resolve) => { answer = resolve; }));
    const user = userEvent.setup();
    renderApp('/aliment-frais');
    await user.upload(screen.getByLabelText('Prendre une photo de l’aliment'), photo());

    expect(await screen.findByText('Identification en cours…')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Aliment frais' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ouvrir le menu' })).toBeInTheDocument();

    answer(jsonResponse(200, { statut: 'reconnu', label_identifie: 'saumon', resultat: foodDetail(), message: null }));
    expect(await screen.findByText('saumon')).toBeInTheDocument();
  });

  it('Photo not recognised: panel over the camera, focus on its title, "Réessayer" goes back', async () => {
    mockFetch(jsonResponse(200, {
      statut: 'non_reconnu', label_identifie: null, resultat: null,
      message: 'La photo n’a pas permis d’identifier l’aliment.',
    }));
    const user = userEvent.setup();
    renderApp('/aliment-frais');
    await user.upload(screen.getByLabelText('Prendre une photo de l’aliment'), photo());

    const title = await screen.findByRole('heading', { name: 'Aliment non reconnu' });
    expect(title).toHaveFocus();
    expect(screen.getByRole('link', { name: 'Rechercher par nom' })).toHaveAttribute('href', '/recherche');
    expect(screen.getByLabelText('Code-barre')).toBeInTheDocument();
    expect(screen.getByText(/projet étudiant/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Réessayer' }));
    expect(screen.getByLabelText('Prendre une photo de l’aliment')).toBeInTheDocument();
  });

  it('Écrire: title bar, search by name and typed barcode', async () => {
    const user = userEvent.setup();
    renderApp('/recherche');
    expect(screen.getByRole('heading', { level: 1, name: 'Rechercher un aliment' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Écrire' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByText(/projet étudiant/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText('Code-barre'), '3017620422003');
    await user.click(screen.getByRole('button', { name: 'Valider' }));
    expect(await screen.findByText('Produit 3017620422003')).toBeInTheDocument();
  });

  it('Écrire with a term: results, no typed-barcode form', async () => {
    mockFetch(jsonResponse(200, {
      terme: 'saumon', nombre_resultats: 1,
      resultats: [{ id_aliment: 26035, nom: 'Saumon, cru', source: 'CIQUAL', url_image: null, id_categorie: 4 }],
    }));
    renderApp('/recherche?q=saumon');
    expect(await screen.findByRole('link', { name: 'Saumon, cru' })).toHaveAttribute('href', '/aliment/26035');
    expect(screen.queryByLabelText('Code-barre')).not.toBeInTheDocument();
  });
});

describe('Desktop keeps its pages', () => {
  it('/analyser shows the two choice cards', () => {
    mockViewport(1280);
    renderApp('/analyser');
    expect(screen.getByRole('heading', { name: 'Votre aliment a-t-il un code-barre ?' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Code-barre' })).not.toBeInTheDocument();
  });
});
