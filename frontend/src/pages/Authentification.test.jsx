import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route } from 'react-router-dom';
import { renderWithProviders } from '../test/renderWithProviders';
import { mockFetch, jsonResponse } from '../test/mockFetch';
import { getToken } from '../services/token';
import Authentification from './Authentification';

const TOKEN_RESPONSE = {
  access_token: 'jwt.real.token',
  token_type: 'bearer',
  user: { id: 7, email: 'lea@example.com', role: 'user' },
};

function renderAuth(route) {
  return renderWithProviders(
    <Routes>
      <Route path="/connexion" element={<Authentification />} />
      <Route path="/inscription" element={<Authentification />} />
      <Route path="/" element={<p>Page d’accueil</p>} />
    </Routes>,
    { route },
  );
}

describe('Login page (POST /auth/login)', () => {
  it('success: stores the token and goes back to the home page', async () => {
    const fetchMock = mockFetch(jsonResponse(200, TOKEN_RESPONSE));
    const user = userEvent.setup();
    renderAuth('/connexion');

    await user.type(screen.getByLabelText('Email'), 'lea@example.com');
    await user.type(screen.getByLabelText('Mot de passe'), 'motdepasse');
    await user.click(screen.getByRole('button', { name: 'Se connecter' }));

    expect(await screen.findByText('Page d’accueil')).toBeInTheDocument();
    expect(getToken()).toBe('jwt.real.token');
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/auth\/login$/);
    expect(JSON.parse(options.body)).toEqual({ email: 'lea@example.com', password: 'motdepasse' });
  });

  it('401: shows the API message and stores no token', async () => {
    mockFetch(jsonResponse(401, { detail: 'Email ou mot de passe incorrect.' }));
    const user = userEvent.setup();
    renderAuth('/connexion');

    await user.type(screen.getByLabelText('Email'), 'lea@example.com');
    await user.type(screen.getByLabelText('Mot de passe'), 'mauvais');
    await user.click(screen.getByRole('button', { name: 'Se connecter' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Email ou mot de passe incorrect.');
    expect(getToken()).toBeNull();
  });

  it('server error: shows a "service unavailable" message', async () => {
    mockFetch(jsonResponse(500));
    const user = userEvent.setup();
    renderAuth('/connexion');

    await user.type(screen.getByLabelText('Email'), 'lea@example.com');
    await user.type(screen.getByLabelText('Mot de passe'), 'motdepasse');
    await user.click(screen.getByRole('button', { name: 'Se connecter' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/momentanément indisponible/);
  });

  it('invalid email: no request is sent, the field is flagged', async () => {
    const fetchMock = mockFetch();
    const user = userEvent.setup();
    renderAuth('/connexion');

    await user.type(screen.getByLabelText('Email'), 'pas-un-email');
    await user.type(screen.getByLabelText('Mot de passe'), 'x');
    await user.click(screen.getByRole('button', { name: 'Se connecter' }));

    expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('Email')).toHaveFocus();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('Sign-up page (POST /auth/register)', () => {
  it('requires 8 characters and the consent box before sending', async () => {
    const fetchMock = mockFetch();
    const user = userEvent.setup();
    renderAuth('/inscription');

    await user.type(screen.getByLabelText('Email'), 'lea@example.com');
    await user.type(screen.getByLabelText('Mot de passe'), 'court');
    await user.click(screen.getByRole('button', { name: 'Créer mon compte' }));
    expect(screen.getByText(/au moins 8 caractères/)).toBeInTheDocument();

    await user.type(screen.getByLabelText('Mot de passe'), '-assez-long');
    await user.click(screen.getByRole('button', { name: 'Créer mon compte' }));
    expect(screen.getByText('Cochez la case pour créer votre compte.')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('success: sends consentement=true and logs the user in', async () => {
    const fetchMock = mockFetch(jsonResponse(201, TOKEN_RESPONSE));
    const user = userEvent.setup();
    renderAuth('/inscription');

    await user.type(screen.getByLabelText('Email'), 'lea@example.com');
    await user.type(screen.getByLabelText('Mot de passe'), 'motdepasse-long');
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Créer mon compte' }));

    expect(await screen.findByText('Page d’accueil')).toBeInTheDocument();
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/auth\/register$/);
    expect(JSON.parse(options.body)).toEqual({
      email: 'lea@example.com',
      password: 'motdepasse-long',
      consentement: true,
    });
    expect(getToken()).toBe('jwt.real.token');
  });

  it('409: shows "account already exists"', async () => {
    mockFetch(jsonResponse(409, { detail: 'Un compte existe déjà avec cet email.' }));
    const user = userEvent.setup();
    renderAuth('/inscription');

    await user.type(screen.getByLabelText('Email'), 'lea@example.com');
    await user.type(screen.getByLabelText('Mot de passe'), 'motdepasse-long');
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Créer mon compte' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Un compte existe déjà');
  });
});

describe('Session restore and expiry (GET /auth/me)', () => {
  it('expired token at startup: cleared silently, user stays on the page', async () => {
    localStorage.setItem('alimendo_token', 'expired');
    mockFetch(jsonResponse(401, { detail: 'Jeton absent, invalide ou expiré.' }));
    renderAuth('/');

    await waitFor(() => expect(getToken()).toBeNull());
    expect(screen.getByText('Page d’accueil')).toBeInTheDocument();
  });

  it('shows the "session expired" notice when redirected after a 401', () => {
    renderWithProviders(
      <Routes>
        <Route path="/connexion" element={<Authentification />} />
      </Routes>,
      { route: { pathname: '/connexion', state: { reason: 'expired', from: '/chatbot' } } },
    );
    expect(screen.getByRole('status')).toHaveTextContent('Votre session a expiré');
  });
});