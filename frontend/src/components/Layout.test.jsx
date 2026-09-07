import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/renderWithProviders';
import Layout from './Layout';

test('affiche le disclaimer médical', () => {
  renderWithProviders(<Layout />);
  expect(screen.getByText(/projet étudiant/i)).toBeInTheDocument();
});