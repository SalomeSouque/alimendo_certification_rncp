import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route, useLocation } from 'react-router-dom';
import { renderWithProviders } from '../test/renderWithProviders';
import { mockFetch, jsonResponse } from '../test/mockFetch';
import { api } from '../services/api';
import { useAuth } from './AuthContext';

function ProtectedPage() {
  const { user } = useAuth();
  return (
    <>
      <p>Connectée : {user?.email ?? 'non'}</p>
      <button onClick={() => api.post('/ai/chat', { question: 'q' }).catch(() => {})}>Appeler</button>
    </>
  );
}

function LoginPage() {
  const { state } = useLocation();
  return <p>Page connexion, raison : {state?.reason}, origine : {state?.from}</p>;
}

it('logged-in user + 401 on a protected call: redirected to /connexion with the reason', async () => {
  localStorage.setItem('alimendo_token', 'valid-then-expired');
  mockFetch(
    jsonResponse(200, { id: 7, email: 'lea@example.com', role: 'user' }), // GET /auth/me
    jsonResponse(401, { detail: 'Jeton absent, invalide ou expiré.' }), // POST /ai/chat
  );
  const user = userEvent.setup();
  renderWithProviders(
    <Routes>
      <Route path="/chatbot" element={<ProtectedPage />} />
      <Route path="/connexion" element={<LoginPage />} />
    </Routes>,
    { route: '/chatbot' },
  );

  expect(await screen.findByText('Connectée : lea@example.com')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Appeler' }));

  expect(
    await screen.findByText('Page connexion, raison : expired, origine : /chatbot'),
  ).toBeInTheDocument();
  expect(localStorage.getItem('alimendo_token')).toBeNull();
});