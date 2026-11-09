import { screen } from '@testing-library/react';
import { Routes, Route } from 'react-router-dom';
import { renderWithProviders } from '../test/renderWithProviders';
import { mockFetch, jsonResponse } from '../test/mockFetch';
import { ADMIN_USER } from '../test/fixtures';
import AdminRoute from './AdminRoute';
import Header from './Header';

function renderAdminRoute() {
  return renderWithProviders(
    <Routes>
      <Route path="/admin" element={<AdminRoute><p>Contenu admin</p></AdminRoute>} />
      <Route path="/connexion" element={<p>Page connexion</p>} />
      <Route path="/" element={<p>Page accueil</p>} />
    </Routes>,
    { route: '/admin' },
  );
}

describe('AdminRoute (/admin reserved to the admin role)', () => {
  it('logged out: redirects to the login page', async () => {
    renderAdminRoute();
    expect(await screen.findByText('Page connexion')).toBeInTheDocument();
    expect(screen.queryByText('Contenu admin')).not.toBeInTheDocument();
  });

  it('logged in without the admin role: redirects to the home page', async () => {
    localStorage.setItem('alimendo_token', 'user-token');
    mockFetch(jsonResponse(200, { id: 7, email: 'lea@exemple.fr', role: 'user', acces_ia: false }));
    renderAdminRoute();
    expect(await screen.findByText('Page accueil')).toBeInTheDocument();
    expect(screen.queryByText('Contenu admin')).not.toBeInTheDocument();
  });

  it('admin: shows the page', async () => {
    localStorage.setItem('alimendo_token', 'admin-token');
    mockFetch(jsonResponse(200, ADMIN_USER));
    renderAdminRoute();
    expect(await screen.findByText('Contenu admin')).toBeInTheDocument();
  });
});

describe('Header admin link', () => {
  it('shown to an admin', async () => {
    localStorage.setItem('alimendo_token', 'admin-token');
    mockFetch(jsonResponse(200, ADMIN_USER));
    renderWithProviders(<Header />);
    expect(await screen.findByRole('link', { name: 'Admin' })).toHaveAttribute('href', '/admin');
  });

  it('hidden from a regular account', async () => {
    localStorage.setItem('alimendo_token', 'user-token');
    mockFetch(jsonResponse(200, { id: 7, email: 'lea@exemple.fr', role: 'user', acces_ia: true }));
    renderWithProviders(<Header />);
    expect(await screen.findByRole('button', { name: 'Se déconnecter' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Admin' })).not.toBeInTheDocument();
  });
});
