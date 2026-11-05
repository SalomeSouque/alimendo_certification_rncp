import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route, useParams } from 'react-router-dom';
import { renderWithProviders } from '../test/renderWithProviders';
import ProduitEmballe from './ProduitEmballe';

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

it('invalid barcode: error linked to the field, focus kept', async () => {
  const user = userEvent.setup();
  renderPage();
  await user.type(screen.getByLabelText('Code-barre'), '12AB');
  await user.click(screen.getByRole('button', { name: 'Valider' }));
  const input = screen.getByLabelText('Code-barre');
  expect(input).toHaveAttribute('aria-invalid', 'true');
  expect(input).toHaveAccessibleDescription(/entre 8 et 14 chiffres/);
  expect(input).toHaveFocus();
});

it('valid barcode with spaces: opens /produit/:code without spaces', async () => {
  const user = userEvent.setup();
  renderPage();
  await user.type(screen.getByLabelText('Code-barre'), '3 017620 422003');
  await user.click(screen.getByRole('button', { name: 'Valider' }));
  expect(await screen.findByText('Produit 3017620422003')).toBeInTheDocument();
});
