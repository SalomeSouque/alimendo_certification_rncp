import { screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route, useParams } from 'react-router-dom';
import { renderWithProviders } from '../test/renderWithProviders';
import ProduitEmballe from '../pages/ProduitEmballe';
import * as barcode from '../services/barcode';

vi.mock('../services/barcode', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    isCameraSupported: vi.fn(() => true),
    decodeBarcodeFromFile: vi.fn(),
    startCameraScan: vi.fn(),
  };
});

function ProductStub() {
  return <p>Produit {useParams().code}</p>;
}

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/produit-emballe" element={<ProduitEmballe />} />
      <Route path="/produit/:code" element={<ProductStub />} />
    </Routes>,
    { route: '/produit-emballe' },
  );
}

const photo = () => new File([new Uint8Array(10)], 'code.jpg', { type: 'image/jpeg' });
const fileInput = () => screen.getByLabelText('Importer une photo du code-barre');

describe('Barcode scan (camera and photo, read in the browser)', () => {
  beforeEach(() => {
    barcode.isCameraSupported.mockReturnValue(true);
  });

  it('photo with a readable barcode: opens the product page', async () => {
    barcode.decodeBarcodeFromFile.mockResolvedValue('3017620422003');
    renderPage();
    fireEvent.change(fileInput(), { target: { files: [photo()] } });
    expect(await screen.findByText('Produit 3017620422003')).toBeInTheDocument();
  });

  it('photo without a readable barcode: message, stays on the page', async () => {
    barcode.decodeBarcodeFromFile.mockResolvedValue(null);
    renderPage();
    fireEvent.change(fileInput(), { target: { files: [photo()] } });
    expect(await screen.findByRole('alert')).toHaveTextContent('Aucun code-barre lisible');
  });

  it('camera: shows the guidance, then opens the product page when a code is read', async () => {
    let emit;
    const stop = vi.fn();
    barcode.startCameraScan.mockImplementation(async (_video, onCode) => { emit = onCode; return { stop }; });
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: 'Scanner avec la caméra' }));
    expect(await screen.findByText('Visez le code-barre : la lecture est automatique.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Arrêter la caméra' })).toBeInTheDocument();

    emit('76012345');
    expect(await screen.findByText('Produit 76012345')).toBeInTheDocument();
  });

  it('camera permission refused: clear message, photo and manual entry still available', async () => {
    barcode.startCameraScan.mockRejectedValue(Object.assign(new Error('denied'), { name: 'NotAllowedError' }));
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: 'Scanner avec la caméra' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('L’accès à la caméra a été refusé');
    expect(fileInput()).toBeInTheDocument();
    expect(screen.getByLabelText('Code-barre')).toBeInTheDocument();
  });

  it('stopping the camera releases it', async () => {
    const stop = vi.fn();
    barcode.startCameraScan.mockResolvedValue({ stop });
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: 'Scanner avec la caméra' }));
    await user.click(await screen.findByRole('button', { name: 'Arrêter la caméra' }));

    expect(stop).toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Scanner avec la caméra' })).toBeInTheDocument();
  });

  it('no camera API (e.g. page served over plain http): no camera button, photo still offered', () => {
    barcode.isCameraSupported.mockReturnValue(false);
    renderPage();
    expect(screen.queryByRole('button', { name: 'Scanner avec la caméra' })).not.toBeInTheDocument();
    expect(fileInput()).toBeInTheDocument();
  });
});

describe('cameraErrorMessage', () => {
  it('maps browser errors to user messages', async () => {
    const { cameraErrorMessage } = await vi.importActual('../services/barcode');
    expect(cameraErrorMessage({ name: 'NotFoundError' })).toMatch(/Aucune caméra/);
    expect(cameraErrorMessage({ name: 'Other' })).toMatch(/n’a pas pu démarrer/);
  });
});
