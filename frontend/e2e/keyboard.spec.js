// e2e/keyboard.spec.js
// Keyboard-only use of the site (WCAG 2.1.1 Keyboard, 2.1.2 No keyboard trap,
// 2.4.3 Focus order, 2.4.7 Focus visible). No mouse click anywhere in this file.
//
// 1. Tour of each page with Tab: every focusable element is reached, the tour comes
//    back to the start (no trap), and each stop has a visible focus indicator
//    (the screen changes when the element gets the focus).
// 2. The main journeys done with the keyboard only: login, search → food → alternative
//    → back, barcode, photo, chatbot, phone menu, "En savoir plus" panels.
//
// Run on one phone width and one desktop width (the other widths add nothing here).
// The list of stops of every page is saved in e2e/captures/<width>/clavier-<page>.json.

import { mkdirSync, writeFileSync } from 'node:fs';
import { test, expect } from '@playwright/test';
import { mockApi } from './support/mockApi.js';

const PROJECTS = ['mobile-390', 'desktop-1280'];
const PHOTO = new URL('../public/assets/saumon.png', import.meta.url).pathname;
const CAPTURES_DIR = new URL('./captures/', import.meta.url);

test.beforeEach(async ({ browserName }, testInfo) => {
  void browserName;
  test.skip(!PROJECTS.includes(testInfo.project.name), 'parcours clavier : 390 et 1280 px seulement');
});

/** Short description of the focused element, for the report. */
function describeFocus(page) {
  return page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) return null;
    const name = el.getAttribute('aria-label') || el.labels?.[0]?.textContent || el.textContent || el.getAttribute('placeholder') || '';
    return {
      id: el.dataset.kbId ?? null,
      element: el.tagName.toLowerCase() + (el.type && el.tagName === 'INPUT' ? `[type=${el.type}]` : ''),
      name: name.trim().replace(/\s+/g, ' ').slice(0, 50),
    };
  });
}

/**
 * Is the focus visible? Screenshot with the focus, then without it (blur): if nothing
 * changes on screen, a keyboard user cannot see where they are. The focus is then
 * given back to the element so the tour goes on from it.
 */
async function focusIsVisible(page) {
  const focused = await page.screenshot({ animations: 'disabled' });
  const handle = await page.evaluateHandle(() => document.activeElement);
  await handle.evaluate((el) => el.blur());
  const blurred = await page.screenshot({ animations: 'disabled' });
  await handle.evaluate((el) => el.focus({ preventScroll: true }));
  return !focused.equals(blurred);
}

/**
 * Tab through the whole page. Every element that should be reachable gets a
 * data-kb-id first, to check afterwards that none was skipped.
 */
async function tabTour(page) {
  const expected = await page.evaluate(() => {
    const selector = 'a[href], button, input, select, textarea, summary, [tabindex]';
    const tabbable = [...document.querySelectorAll(selector)].filter((el) => {
      if (el.disabled || el.tabIndex < 0 || el.closest('[inert]')) return false;
      if (el.type === 'hidden') return false;
      // A visually hidden input inside a visible label (file inputs) is reachable.
      const box = el.matches('.sr-only') ? el.parentElement : el;
      return box.checkVisibility({ visibilityProperty: true });
    });
    tabbable.forEach((el, i) => { el.dataset.kbId = String(i); });
    return tabbable.length;
  });

  // When a field takes the focus on load (chatbot), the tour starts there: after the
  // last element the focus leaves the page once, then comes back to the top.
  const stops = [];
  let leftPage = false;
  for (let i = 0; i < expected + 5; i += 1) {
    await page.keyboard.press('Tab');
    const focus = await describeFocus(page);
    if (focus === null) {
      if (leftPage || stops.length === 0) break;
      leftPage = true; // past the last element: the browser, then the top of the page
      continue;
    }
    if (stops.length > 0 && focus.id !== null && focus.id === stops[0].id) break; // looped
    stops.push({ ...focus, visible: await focusIsVisible(page) });
  }
  return { expected, stops };
}

/** Press Tab until `locator` has the focus (fails after `max` presses). */
async function tabTo(page, locator, max = 80) {
  for (let i = 0; i < max; i += 1) {
    await page.keyboard.press('Tab');
    if (await locator.evaluate((el) => el === document.activeElement)) return;
  }
  throw new Error(`Élément jamais atteint au clavier : ${locator}`);
}

const PAGES = [
  { name: 'accueil', path: '/' },
  { name: 'analyser', path: '/analyser' },
  { name: 'recherche', path: '/recherche?q=saumon' },
  { name: 'aliment', path: '/aliment/26035' },
  { name: 'produit-emballe', path: '/produit-emballe' },
  { name: 'en-savoir-plus', path: '/en-savoir-plus' },
  { name: 'connexion', path: '/connexion' },
  { name: 'inscription', path: '/inscription' },
  { name: 'page-inconnue', path: '/cette-page-n-existe-pas' },
  { name: 'confidentialite', path: '/confidentialite' },
  { name: 'chatbot-deconnecte', path: '/chatbot' },
  { name: 'chatbot', path: '/chatbot', auth: true },
  { name: 'aliment-frais', path: '/aliment-frais', auth: true },
];

test.describe('tour au clavier', () => {
  for (const p of PAGES) {
    test(p.name, async ({ page }, testInfo) => {
      await mockApi(page, p);
      await page.goto(p.path);
      await page.waitForLoadState('networkidle');
      const { expected, stops } = await tabTour(page);

      const dir = new URL(`${testInfo.project.name}/`, CAPTURES_DIR);
      mkdirSync(dir, { recursive: true });
      writeFileSync(new URL(`clavier-${p.name}.json`, dir), JSON.stringify({ page: p.path, expected, stops }, null, 2));

      const reached = new Set(stops.map((s) => s.id));
      const missed = [...Array(expected).keys()].map(String).filter((id) => !reached.has(id));
      expect.soft(missed, 'éléments jamais atteints avec Tab').toEqual([]);
      expect.soft(stops.filter((s) => !s.visible), 'focus invisible').toEqual([]);
      expect(stops.length, 'au moins un élément atteint').toBeGreaterThan(0);
    });
  }
});

test.describe('parcours au clavier', () => {
  test('connexion', async ({ page }) => {
    await mockApi(page);
    await page.goto('/connexion');
    await tabTo(page, page.getByLabel('Email'));
    await page.keyboard.type('lea.dupont@exemple.fr');
    await tabTo(page, page.getByLabel('Mot de passe', { exact: true }));
    await page.keyboard.type('motdepasse-e2e');
    await tabTo(page, page.locator('form button[type=submit]'));
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL('/');
  });

  test('connexion : erreur annoncée et focus sur le champ', async ({ page }) => {
    await mockApi(page);
    await page.goto('/connexion');
    await tabTo(page, page.locator('form button[type=submit]'));
    await page.keyboard.press('Enter');
    // The first invalid field gets the focus, with its message linked to it.
    await expect(page.getByLabel('Email')).toBeFocused();
    await expect(page.getByLabel('Email')).toHaveAttribute('aria-invalid', 'true');
  });

  test('recherche → aliment → alternative → retour', async ({ page }) => {
    await mockApi(page);
    await page.goto('/recherche');
    await tabTo(page, page.getByRole('searchbox').or(page.getByRole('textbox')).first());
    await page.keyboard.type('saumon');
    await page.keyboard.press('Enter');
    const first = page.getByRole('link', { name: /Saumon atlantique, sauvage, cru/ });
    await tabTo(page, first);
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL('/aliment/26035');
    await tabTo(page, page.getByRole('link', { name: /Maquereau/ }));
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL('/aliment/26050');
    await tabTo(page, page.getByRole('link', { name: /Retour/ }));
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL('/aliment/26035');
  });

  test('code-barre saisi à la main', async ({ page }, testInfo) => {
    // Phones: the analysis screen opens the camera; typing goes through the "Écrire" tab.
    test.skip(testInfo.project.name.startsWith('mobile'), 'saisie manuelle : version ordinateur');
    await mockApi(page);
    await page.goto('/produit-emballe');
    await tabTo(page, page.getByRole('textbox', { name: 'Code-barre' }));
    await page.keyboard.type('3017620422003');
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL('/produit/3017620422003');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('photo d’un aliment', async ({ page }, testInfo) => {
    await mockApi(page, { auth: true });
    await page.goto('/aliment-frais');
    const input = testInfo.project.name.startsWith('mobile')
      ? page.getByLabel('Prendre une photo de l’aliment')
      : page.locator('.dropzone input[type=file]');
    await tabTo(page, input);
    // Enter on a file field opens the file picker: the test answers it.
    const chooser = page.waitForEvent('filechooser');
    await page.keyboard.press('Enter');
    await (await chooser).setFiles(PHOTO);
    // The result takes the focus: a screen reader announces it, Tab goes on from it.
    await expect(page.locator('.analyse-recognised')).toBeVisible();
    await expect(page.locator('.analyse-recognised')).toBeFocused();
  });

  test('chatbot : question et sources', async ({ page }) => {
    await mockApi(page, { auth: true });
    await page.goto('/chatbot');
    await tabTo(page, page.getByRole('textbox', { name: 'Poser une question' }));
    await page.keyboard.type('Le saumon est-il intéressant pour moi ?');
    await page.keyboard.press('Enter');
    const source = page.getByRole('link', { name: /Dietary factors and endometriosis/ });
    await expect(source).toBeVisible();
    await tabTo(page, source);
  });

  test('menu du téléphone : ouverture, focus piégé, Échap', async ({ page }, testInfo) => {
    test.skip(!testInfo.project.name.startsWith('mobile'), 'menu ☰ : téléphone');
    await mockApi(page);
    await page.goto('/aliment/26035');
    const burger = page.getByRole('button', { name: 'Ouvrir le menu' });
    await tabTo(page, burger);
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog', { name: 'Menu' });
    await expect(dialog).toBeVisible();
    for (let i = 0; i < 20; i += 1) {
      await page.keyboard.press('Tab');
      expect(await dialog.evaluate((d) => d.contains(document.activeElement)), 'focus resté dans le menu').toBe(true);
    }
    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
    await expect(burger).toBeFocused();
  });

  test('« En savoir plus » : panneaux dépliables', async ({ page }) => {
    await mockApi(page);
    await page.goto('/en-savoir-plus');
    const summary = page.locator('details.acc-item:not([open]) > summary').first();
    const details = page.locator('details.acc-item:not([open])').first();
    const handle = await details.elementHandle();
    await tabTo(page, summary);
    await page.keyboard.press('Enter');
    expect(await handle.evaluate((d) => d.open)).toBe(true);
    await page.keyboard.press('Space');
    expect(await handle.evaluate((d) => d.open)).toBe(false);
  });
});
