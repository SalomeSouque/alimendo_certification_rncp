// Phone layouts of the content pages (maquettes accueil, M4a, M4b, M6, M7).
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route } from 'react-router-dom';
import { renderWithProviders } from '../test/renderWithProviders';
import { mockFetch, jsonResponse } from '../test/mockFetch';
import { mockViewport } from '../test/viewport';
import { foodDetail, CATEGORIES } from '../test/fixtures';
import { resetCategoriesCache } from '../services/score';
import Home from './Home';
import Aliment from './Aliment';
import AlimentFrais from './AlimentFrais';
import EnSavoirPlus from './EnSavoirPlus';
import FoodScore from '../components/FoodScore';

beforeEach(() => resetCategoriesCache());

describe('Home', () => {
  it('phone: the picture comes between the title and the text', () => {
    mockViewport(360);
    renderWithProviders(<Home />);
    const hero = screen.getByRole('heading', { level: 1 }).closest('section');
    expect(within(hero).getByRole('img', { name: 'Personne allongée sur un canapé' })).toBeInTheDocument();
  });

  it('desktop: the picture stays outside the hero text', () => {
    renderWithProviders(<Home />);
    const hero = screen.getByRole('heading', { level: 1 }).closest('section');
    expect(within(hero).queryByRole('img', { name: 'Personne allongée sur un canapé' })).not.toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Personne allongée sur un canapé' })).toBeInTheDocument();
  });

  it('phone: the yellow line comes in 5 decorative pieces, one per section', () => {
    mockViewport(360);
    const { container } = renderWithProviders(<Home />);
    const pieces = container.querySelectorAll('img.home-line');
    expect(pieces).toHaveLength(5);
    pieces.forEach((img) => expect(img).toHaveAttribute('aria-hidden', 'true'));
    expect(container.querySelector('.wave-home')).toBeNull();
  });

  it('desktop: a single line behind the whole page', () => {
    const { container } = renderWithProviders(<Home />);
    expect(container.querySelector('.wave-home')).toHaveAttribute('src', '/assets/yellow_line_home_page.svg');
    expect(container.querySelectorAll('img.home-line')).toHaveLength(0);
  });
});

describe('Food score', () => {
  it('phone: the verdict sits under the name, not in the score card', () => {
    mockViewport(360);
    const { container } = renderWithProviders(<FoodScore detail={foodDetail()} />);
    expect(container.querySelector('.food-verdict')).toHaveTextContent('Modérément anti-inflammatoire');
    expect(container.querySelector('.score-card .score-verdict')).toBeNull();
  });

  it('desktop: the verdict stays in the score card', () => {
    const { container } = renderWithProviders(<FoodScore detail={foodDetail()} />);
    expect(container.querySelector('.score-card .score-verdict')).toHaveTextContent('Modérément anti-inflammatoire');
    expect(container.querySelector('.food-verdict')).toBeNull();
  });
});

describe('Food page "Retour"', () => {
  function renderFrom(route) {
    return renderWithProviders(
      <Routes>
        <Route path="/recherche" element={<p>Résultats</p>} />
        <Route path="/aliment/:id" element={<Aliment />} />
      </Routes>,
      { route },
    );
  }

  it('opened directly: links to the search page', async () => {
    mockFetch(jsonResponse(200, foodDetail()), jsonResponse(200, CATEGORIES));
    renderFrom('/aliment/26035');
    await screen.findByRole('heading', { level: 1, name: 'Saumon, cru' });
    expect(screen.getByRole('link', { name: '← Retour' })).toHaveAttribute('href', '/recherche');
  });
});

describe('Photo result on a phone (maquette M4b)', () => {
  it('"Retour" goes back to the camera; the title stays for screen readers', async () => {
    mockViewport(360);
    mockFetch(jsonResponse(200, { statut: 'reconnu', label_identifie: 'saumon', resultat: foodDetail(), message: null }));
    const user = userEvent.setup();
    renderWithProviders(<AlimentFrais />);
    await user.upload(
      screen.getByLabelText('Prendre une photo de l’aliment'),
      new File([new Uint8Array(10)], 'photo.jpg', { type: 'image/jpeg' }),
    );

    expect(await screen.findByText('saumon')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Aliment frais' })).toHaveClass('sr-only');
    await user.click(screen.getByRole('button', { name: '← Retour' }));
    expect(screen.getByLabelText('Prendre une photo de l’aliment')).toBeInTheDocument();
  });
});

describe('En savoir plus', () => {
  it('the score scale is a valid definition list (value → meaning)', () => {
    renderWithProviders(<EnSavoirPlus />);
    const terms = screen.getAllByRole('term').map((t) => t.textContent);
    expect(terms).toEqual(['-2', '-1', '0', '+1', '+2']);
    expect(screen.getAllByRole('definition')[0]).toHaveTextContent('très anti-inflammatoire');
  });
});
