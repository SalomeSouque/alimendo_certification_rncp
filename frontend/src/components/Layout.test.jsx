import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Layout from './Layout.jsx';

describe('Layout', () => {
  it('affiche le disclaimer médical', () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    );
    expect(
      screen.getByText(/ne remplace pas un suivi médical/i)
    ).toBeInTheDocument();
  });
});