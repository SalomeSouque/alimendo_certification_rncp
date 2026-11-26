import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/renderWithProviders';
import { mockFetch, jsonResponse } from '../test/mockFetch';
import { mockViewport } from '../test/viewport';
import Header from './Header';

const USER = { id: 7, email: 'lea@exemple.fr', role: 'user', acces_ia: true };

describe('Header: desktop navigation, burger menu below 1024 px (maquette M1)', () => {
  it('desktop: full navigation, no burger button', () => {
    renderWithProviders(<Header />);
    expect(screen.getByRole('link', { name: 'Analyser un aliment' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Ouvrir le menu' })).not.toBeInTheDocument();
  });

  it('phone, logged out: burger, logo and an account icon leading to the login page', () => {
    mockViewport(360);
    renderWithProviders(<Header />);
    expect(screen.getByRole('button', { name: 'Ouvrir le menu' })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('link', { name: 'Se connecter' })).toHaveAttribute('href', '/connexion');
    expect(screen.queryByRole('link', { name: 'Analyser un aliment' })).not.toBeInTheDocument();
  });

  it('opens the drawer: links, active page, "Projet étudiant"', async () => {
    mockViewport(360);
    const user = userEvent.setup();
    renderWithProviders(<Header />, { route: '/chatbot' });
    await user.click(screen.getByRole('button', { name: 'Ouvrir le menu' }));

    const drawer = screen.getByRole('dialog', { name: 'Menu' });
    expect(drawer).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Chatbot' })).toHaveClass('active');
    expect(screen.getByRole('link', { name: 'Accueil' })).not.toHaveClass('active');
    expect(drawer).toHaveTextContent(/projet étudiant/i);
    // Focus moves inside the drawer, the page behind does not scroll.
    expect(drawer).toContainElement(document.activeElement);
    expect(document.body.style.overflow).toBe('hidden');
  });

  it('Escape closes the drawer and gives the focus back to the burger', async () => {
    mockViewport(360);
    const user = userEvent.setup();
    renderWithProviders(<Header />);
    const burger = screen.getByRole('button', { name: 'Ouvrir le menu' });
    await user.click(burger);
    await user.keyboard('{Escape}');

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(burger).toHaveFocus();
    expect(document.body.style.overflow).toBe('');
  });

  it('✕ and the dimmed background close the drawer', async () => {
    mockViewport(360);
    const user = userEvent.setup();
    renderWithProviders(<Header />);
    await user.click(screen.getByRole('button', { name: 'Ouvrir le menu' }));
    await user.click(screen.getByRole('button', { name: 'Fermer le menu' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Ouvrir le menu' }));
    await user.click(document.querySelector('.drawer-backdrop'));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('Tab stays inside the drawer', async () => {
    mockViewport(360);
    const user = userEvent.setup();
    renderWithProviders(<Header />);
    await user.click(screen.getByRole('button', { name: 'Ouvrir le menu' }));
    const drawer = screen.getByRole('dialog', { name: 'Menu' });
    for (let i = 0; i < 10; i += 1) {
      await user.tab();
      expect(drawer).toContainElement(document.activeElement);
    }
  });

  it('logged in: the account icon opens the menu, which offers "Se déconnecter"', async () => {
    mockViewport(360);
    localStorage.setItem('alimendo_token', 'user-token');
    mockFetch(jsonResponse(200, USER));
    const user = userEvent.setup();
    renderWithProviders(<Header />);

    await user.click(await screen.findByRole('button', { name: /Mon compte/ }));
    await user.click(screen.getByRole('button', { name: 'Se déconnecter' }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('link', { name: 'Se connecter' })).toBeInTheDocument());
    expect(localStorage.getItem('alimendo_token')).toBeNull();
  });
});
