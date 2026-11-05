import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route } from 'react-router-dom';
import { renderWithProviders } from '../test/renderWithProviders';
import { mockFetch, jsonResponse } from '../test/mockFetch';
import Chatbot from './Chatbot';

const SHORT_DISCLAIMER =
  'Information générale issue d’un corpus documentaire limité. Ne remplace pas un avis médical.';

function renderChat() {
  return renderWithProviders(
    <Routes>
      <Route path="/chatbot" element={<Chatbot />} />
      <Route path="/connexion" element={<p>Page connexion</p>} />
      <Route path="/analyser" element={<p>Page analyser</p>} />
    </Routes>,
    { route: '/chatbot' },
  );
}

async function ask(user, question) {
  await user.type(screen.getByLabelText('Poser une question'), question);
  await user.click(screen.getByRole('button', { name: 'Envoyer' }));
}

describe('Chatbot (POST /ai/chat)', () => {
  it('shows the §7.7 banner and the privacy notice linked to the input', () => {
    renderChat();
    expect(screen.getByText('Projet étudiant — prototype de démonstration.')).toBeInTheDocument();
    const input = screen.getByLabelText('Poser une question');
    expect(input).toHaveAccessibleDescription(/N’indiquez pas d’informations personnelles ou de santé/);
  });

  it('success: shows the answer in paragraphs, deduplicated sources and the disclaimer', async () => {
    const fetchMock = mockFetch(
      jsonResponse(200, {
        reponse: 'Premier paragraphe.\n\nSecond paragraphe.',
        intention: 'in_scope',
        action: 'RAG_RETRIEVAL',
        sources: [
          { id_source: 'S2', titre: 'Guideline ESHRE 2022', url: 'https://example.org/eshre', score_similarite: 0.8 },
          { id_source: 'S2', titre: 'Guideline ESHRE 2022', url: 'https://example.org/eshre', score_similarite: 0.7 },
          { id_source: 'S9', titre: 'Fiche Inserm', url: null, score_similarite: 0.6 },
        ],
        disclaimer: 'Information générale issue d’un corpus documentaire limité. Ne remplace pas un avis médical.',
      }),
    );
    const user = userEvent.setup();
    renderChat();

    await ask(user, 'Qu’est-ce que l’endométriose ?');

    const answer = await screen.findByRole('article', { name: 'Réponse de l’assistant' });
    expect(within(answer).getByText('Premier paragraphe.')).toBeInTheDocument();
    expect(within(answer).getByText('Second paragraphe.')).toBeInTheDocument();
    const links = within(answer).getAllByRole('link');
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute('href', 'https://example.org/eshre');
    expect(links[0]).toHaveAttribute('rel', 'noopener noreferrer');
    expect(within(answer).getByText('Fiche Inserm')).toBeInTheDocument();
    expect(within(answer).getByText(SHORT_DISCLAIMER)).toBeInTheDocument();

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/ai\/chat$/);
    expect(JSON.parse(options.body)).toEqual({ question: 'Qu’est-ce que l’endométriose ?' });
  });

  it('shows a loading state while waiting and disables sending', async () => {
    let resolve;
    mockFetch(() => new Promise((r) => { resolve = r; }));
    const user = userEvent.setup();
    renderChat();

    await ask(user, 'Une question');

    expect(screen.getByRole('status')).toHaveTextContent('Recherche dans la documentation');
    expect(screen.getByRole('button', { name: 'Envoyer' })).toBeDisabled();
    resolve(jsonResponse(200, { reponse: 'Ok.', intention: 'in_scope', action: 'RAG_RETRIEVAL', sources: [], disclaimer: null }));
    expect(await screen.findByText('Ok.')).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('REDIRECT_SCAN: offers a link to the food analysis', async () => {
    mockFetch(jsonResponse(200, { reponse: 'Texte §7.2', intention: 'food_specific', action: 'REDIRECT_SCAN', sources: [], disclaimer: SHORT_DISCLAIMER }));
    const user = userEvent.setup();
    renderChat();

    await ask(user, 'Quel est le score du saumon ?');

    const answer = await screen.findByRole('article', { name: 'Réponse de l’assistant' });
    expect(within(answer).getByRole('link', { name: 'Analyser un aliment' })).toHaveAttribute('href', '/analyser');
  });

  it('distress answer (§7.5): no disclaimer and no sources displayed', async () => {
    mockFetch(jsonResponse(200, { reponse: 'Texte §7.5', intention: 'detresse_urgence', action: 'SAFE_RESPONSE_DISTRESS', sources: [], disclaimer: null }));
    const user = userEvent.setup();
    renderChat();

    await ask(user, 'J’ai très mal');

    const answer = await screen.findByRole('article', { name: 'Réponse de l’assistant' });
    expect(within(answer).queryByText(SHORT_DISCLAIMER)).not.toBeInTheDocument();
    expect(within(answer).queryByText('Sources')).not.toBeInTheDocument();
  });

  it('503: shows the API message and retries the same question', async () => {
    const fetchMock = mockFetch(
      jsonResponse(503, { detail: 'Le service de réponse est temporairement indisponible, réessayez dans un instant.' }),
      jsonResponse(200, { reponse: 'Réponse après reprise.', intention: 'in_scope', action: 'RAG_RETRIEVAL', sources: [], disclaimer: SHORT_DISCLAIMER }),
    );
    const user = userEvent.setup();
    renderChat();

    await ask(user, 'Une question');
    expect(await screen.findByRole('alert')).toHaveTextContent('temporairement indisponible');

    await user.click(screen.getByRole('button', { name: 'Réessayer' }));
    expect(await screen.findByText('Réponse après reprise.')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ question: 'Une question' });
  });

  it('401 (expired session): redirected to the login page', async () => {
    localStorage.setItem('alimendo_token', 'expired-soon');
    mockFetch(
      jsonResponse(200, { id: 7, email: 'lea@example.com', role: 'user' }), // GET /auth/me
      jsonResponse(401, { detail: 'Jeton absent, invalide ou expiré.' }),
    );
    const user = userEvent.setup();
    renderChat();
    await screen.findByRole('button', { name: 'Se déconnecter' });

    await ask(user, 'Une question');

    expect(await screen.findByText('Page connexion')).toBeInTheDocument();
  });

  it('question shorter than 3 characters: no request, error linked to the input', async () => {
    const fetchMock = mockFetch();
    const user = userEvent.setup();
    renderChat();

    await ask(user, 'ab');

    const input = screen.getByLabelText('Poser une question');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAccessibleDescription(/au moins 3 caractères/);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
