import { screen } from '@testing-library/react';
import { Routes, Route } from 'react-router-dom';
import { renderWithProviders } from '../test/renderWithProviders';
import { mockFetch, jsonResponse } from '../test/mockFetch';
import AuthGate from './AuthGate';

function renderGate(feature) {
  return renderWithProviders(
    <Routes>
      <Route path="/chatbot" element={<AuthGate feature={feature}><p>Contenu protégé</p></AuthGate>} />
    </Routes>,
    { route: '/chatbot' },
  );
}

describe('AuthGate (access to the AI features)', () => {
  it('logged out: shows "connexion requise" with a link to the login page, not the feature', async () => {
    renderGate('chatbot');
    expect(await screen.findByRole('heading', { name: /connexion requise/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Se connecter' })).toHaveAttribute('href', '/connexion');
    expect(screen.queryByText('Contenu protégé')).not.toBeInTheDocument();
  });

  it('logged in (valid token, GET /auth/me 200): shows the feature', async () => {
    localStorage.setItem('alimendo_token', 'valid');
    mockFetch(jsonResponse(200, { id: 7, email: 'lea@example.com', role: 'user' }));
    renderGate('chatbot');
    expect(await screen.findByText('Contenu protégé')).toBeInTheDocument();
  });

  it('expired token at startup (GET /auth/me 401): treated as logged out', async () => {
    localStorage.setItem('alimendo_token', 'expired');
    mockFetch(jsonResponse(401, { detail: 'Jeton absent, invalide ou expiré.' }));
    renderGate('chatbot');
    expect(await screen.findByRole('heading', { name: /connexion requise/ })).toBeInTheDocument();
  });

  it('public feature: no login wall', () => {
    renderGate('recherche');
    expect(screen.getByText('Contenu protégé')).toBeInTheDocument();
  });
});
