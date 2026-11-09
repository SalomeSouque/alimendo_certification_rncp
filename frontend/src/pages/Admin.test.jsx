import { screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route } from 'react-router-dom';
import { vi } from 'vitest';
import { renderWithProviders } from '../test/renderWithProviders';
import { jsonResponse } from '../test/mockFetch';
import { ADMIN_USER, adminAccounts } from '../test/fixtures';
import Admin from './Admin';

/**
 * Fake backend answering by route, so the order of the calls does not matter.
 * `list` and `patch` are the responses (or functions returning one) of
 * GET /admin/utilisateurs and PATCH /admin/utilisateurs/{id}/acces-ia.
 */
function fakeBackend({ list = () => jsonResponse(200, adminAccounts()), patch } = {}) {
  const fn = vi.fn(async (url, options) => {
    const path = new URL(url).pathname;
    if (path === '/auth/me') return jsonResponse(200, ADMIN_USER);
    if (path === '/admin/utilisateurs') return typeof list === 'function' ? list() : list;
    if (options.method === 'PATCH') return patch(url, JSON.parse(options.body));
    throw new Error(`Unexpected call ${options.method} ${path}`);
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}

function patchCalls(fetchMock) {
  return fetchMock.mock.calls.filter(([, options]) => options.method === 'PATCH');
}

function renderAdmin() {
  localStorage.setItem('alimendo_token', 'admin-token');
  return renderWithProviders(
    <Routes>
      <Route path="/admin" element={<Admin />} />
      <Route path="/" element={<p>Page accueil</p>} />
    </Routes>,
    { route: '/admin' },
  );
}

async function findRow(email) {
  const cell = await screen.findByRole('rowheader', { name: new RegExp(email) });
  return cell.closest('tr');
}

describe('Admin page (/admin)', () => {
  it('shows the student project notice and lists the accounts to approve by default', async () => {
    fakeBackend();
    renderAdmin();

    expect(screen.getByRole('heading', { level: 1, name: 'Espace admin' })).toBeInTheDocument();
    expect(screen.getByText('Projet étudiant, prototype de démonstration.')).toBeInTheDocument();
    expect(screen.getByText('Chargement des comptes…')).toBeInTheDocument();

    const row = await findRow('camille.martin@exemple.fr');
    expect(within(row).getByText('8 nov. 2026')).toBeInTheDocument();
    expect(within(row).getByRole('switch', { name: 'Accès IA de camille.martin@exemple.fr' }))
      .toHaveAttribute('aria-checked', 'false');
    expect(screen.queryByText('sophie.l@exemple.fr')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /À valider/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('2 comptes sur 4, du plus récent au plus ancien')).toBeInTheDocument();
  });

  it('filter "Tous": shows every account; the admin cannot change her own access', async () => {
    fakeBackend();
    const user = userEvent.setup();
    renderAdmin();
    await findRow('camille.martin@exemple.fr');

    await user.click(screen.getByRole('button', { name: /Tous/ }));

    const selfRow = await findRow('admin@alimendo.fr');
    expect(within(selfRow).getByText('vous')).toBeInTheDocument();
    const selfSwitch = within(selfRow).getByRole('switch');
    expect(selfSwitch).toBeDisabled();
    expect(selfSwitch).toHaveAccessibleDescription('Votre propre accès se modifie avec le script serveur.');
    expect(within(await findRow('sophie.l@exemple.fr')).getByRole('switch')).toBeEnabled();
  });

  it('search: filters on the email and offers to clear an empty result', async () => {
    fakeBackend();
    const user = userEvent.setup();
    renderAdmin();
    await findRow('camille.martin@exemple.fr');

    await user.type(screen.getByRole('searchbox', { name: 'Rechercher un email' }), 'inconnu');

    expect(screen.getByRole('heading', { name: 'Aucun compte ne correspond à « inconnu »' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Effacer la recherche' }));
    expect(await findRow('jury.simplon@exemple.fr')).toBeInTheDocument();
  });

  it('opening an access: asks for confirmation, sends the PATCH, confirms with a toast', async () => {
    const fetchMock = fakeBackend({
      patch: (url, body) => jsonResponse(200, { ...adminAccounts()[0], acces_ia: body.acces_ia }),
    });
    const user = userEvent.setup();
    renderAdmin();
    const row = await findRow('camille.martin@exemple.fr');

    await user.click(within(row).getByRole('switch'));

    const dialog = screen.getByRole('alertdialog', { name: 'Ouvrir l’accès IA ?' });
    expect(dialog).toHaveTextContent('camille.martin@exemple.fr pourra utiliser le chatbot');
    expect(within(dialog).getByRole('button', { name: 'Annuler' })).toHaveFocus();
    expect(patchCalls(fetchMock)).toHaveLength(0);

    await user.click(within(dialog).getByRole('button', { name: 'Ouvrir l’accès' }));

    expect(await screen.findByText('Accès ouvert pour camille.martin@exemple.fr')).toBeInTheDocument();
    const [url, options] = patchCalls(fetchMock)[0];
    expect(url).toMatch(/\/admin\/utilisateurs\/12\/acces-ia$/);
    expect(JSON.parse(options.body)).toEqual({ acces_ia: true });
    // The account no longer waits for approval: it leaves the default filter.
    expect(screen.queryByRole('rowheader', { name: /camille\.martin/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Accès ouvert/ })).toHaveTextContent('3');
  });

  it('cancel or Escape: closes the dialog without any PATCH', async () => {
    const fetchMock = fakeBackend();
    const user = userEvent.setup();
    renderAdmin();
    const row = await findRow('camille.martin@exemple.fr');
    const toggle = within(row).getByRole('switch');

    await user.click(toggle);
    await user.click(screen.getByRole('button', { name: 'Annuler' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(toggle).toHaveFocus();

    await user.click(toggle);
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(patchCalls(fetchMock)).toHaveLength(0);
  });

  it('closing an access: danger confirmation with the immediate effect', async () => {
    const fetchMock = fakeBackend({
      patch: (url, body) => jsonResponse(200, { ...adminAccounts()[2], acces_ia: body.acces_ia }),
    });
    const user = userEvent.setup();
    renderAdmin();
    await findRow('camille.martin@exemple.fr');
    await user.click(screen.getByRole('button', { name: /Accès ouvert/ }));

    await user.click(within(await findRow('sophie.l@exemple.fr')).getByRole('switch'));
    const dialog = screen.getByRole('alertdialog', { name: 'Fermer l’accès IA ?' });
    expect(dialog).toHaveTextContent('Effet immédiat');
    await user.click(within(dialog).getByRole('button', { name: 'Fermer l’accès' }));

    expect(await screen.findByText('Accès fermé pour sophie.l@exemple.fr')).toBeInTheDocument();
    expect(JSON.parse(patchCalls(fetchMock)[0][1].body)).toEqual({ acces_ia: false });
  });

  it('PATCH failure: keeps the access, shows the error on the row, retry works', async () => {
    const answers = [
      () => { throw new TypeError('Failed to fetch'); },
      () => jsonResponse(200, { ...adminAccounts()[1], acces_ia: true }),
    ];
    const fetchMock = fakeBackend({ patch: () => answers.shift()() });
    const user = userEvent.setup();
    renderAdmin();
    const row = await findRow('jury.simplon@exemple.fr');

    await user.click(within(row).getByRole('switch'));
    await user.click(screen.getByRole('button', { name: 'Ouvrir l’accès' }));

    expect(await within(row).findByRole('alert')).toHaveTextContent(
      'Le serveur est injoignable. Vérifiez votre connexion puis réessayez. L’accès n’a pas changé.',
    );
    expect(within(row).getByRole('switch')).toHaveAttribute('aria-checked', 'false');

    await user.click(within(row).getByRole('button', { name: 'Réessayer' }));

    expect(await screen.findByText('Accès ouvert pour jury.simplon@exemple.fr')).toBeInTheDocument();
    expect(patchCalls(fetchMock)).toHaveLength(2);
  });

  it('list error: explains and reloads on "Réessayer"', async () => {
    const answers = [
      () => jsonResponse(503, { detail: 'Base de données indisponible.' }),
      () => jsonResponse(200, adminAccounts()),
    ];
    fakeBackend({ list: () => answers.shift()() });
    const user = userEvent.setup();
    renderAdmin();

    const panel = await screen.findByRole('alert');
    expect(panel).toHaveTextContent('Impossible de charger les comptes');
    expect(panel).toHaveTextContent('Base de données indisponible.');

    await user.click(within(panel).getByRole('button', { name: 'Réessayer' }));
    expect(await findRow('camille.martin@exemple.fr')).toBeInTheDocument();
  });

  it('403 from the API (admin role removed): shows the reserved access panel', async () => {
    fakeBackend({ list: jsonResponse(403, { detail: 'Accès réservé.' }) });
    renderAdmin();

    expect(await screen.findByRole('heading', { name: 'Accès réservé aux admins' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Retour à l’accueil' })).toHaveAttribute('href', '/');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('nothing to approve: empty state with a shortcut to every account', async () => {
    fakeBackend({ list: () => jsonResponse(200, adminAccounts().map((a) => ({ ...a, acces_ia: true }))) });
    const user = userEvent.setup();
    renderAdmin();

    expect(await screen.findByRole('heading', { name: 'Aucun compte à valider' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Voir tous les comptes' }));
    await waitFor(() => expect(screen.getAllByRole('switch')).toHaveLength(4));
  });
});
