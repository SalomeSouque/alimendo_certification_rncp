// e2e/responsive.spec.js
// Every page (and its important states) is opened at each width of playwright.config.js.
// For each one: no horizontal overflow, no axe violation (WCAG 2.2 AA), form fields
// at 16 px or more on mobile, plus a full-page screenshot in e2e/captures/<width>/.
// Small touch targets are reported as warnings (annotations), they do not fail the test.
//
// The admin page is left out on purpose: it is only used on a computer.

import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { test, expect } from '@playwright/test';
import { mockApi } from './support/mockApi.js';
import { findOverflow, findSmallInputFonts, findSmallTargets, runAxe } from './support/checks.js';

const CAPTURES_DIR = new URL('./captures/', import.meta.url);

async function askQuestion(page) {
  await page.getByRole('textbox', { name: 'Poser une question' }).fill('Le saumon est-il intéressant pour moi ?');
  await page.getByRole('button', { name: 'Envoyer' }).click();
  await page.locator('.msg-bot:not(.msg-typing), .auth-card').first().waitFor();
}

/** Sends a photo, then waits for the screen given by `outcome` (CSS selector). */
const uploadPhoto = (outcome) => async (page) => {
  const buffer = readFileSync(new URL('../public/assets/saumon.png', import.meta.url));
  await page.locator('input[type=file]').first().setInputFiles({ name: 'photo.png', mimeType: 'image/png', buffer });
  await page.locator(outcome).first().waitFor();
};

async function openMenu(page) {
  await page.getByRole('button', { name: 'Ouvrir le menu' }).click();
  await page.getByRole('dialog', { name: 'Menu' }).waitFor();
}

const SCENARIOS = [
  { name: 'accueil', path: '/' },
  // Burger menu: below 1024 px only (maquette M1).
  { name: 'menu-ouvert', path: '/aliment/26035', act: openMenu, compactOnly: true },
  { name: 'analyser', path: '/analyser' },
  { name: 'recherche-vide', path: '/recherche' },
  { name: 'recherche', path: '/recherche?q=saumon' },
  { name: 'recherche-aucun-resultat', path: '/recherche?q=xyzw' },
  { name: 'aliment-ciqual', path: '/aliment/26035' },
  { name: 'produit-code-barre', path: '/produit/3017620422003' },
  { name: 'produit-emballe', path: '/produit-emballe' },
  { name: 'en-savoir-plus', path: '/en-savoir-plus' },
  { name: 'connexion', path: '/connexion' },
  { name: 'inscription', path: '/inscription' },
  { name: 'page-inconnue', path: '/cette-page-n-existe-pas' },
  { name: 'mentions-legales', path: '/mentions-legales' },
  { name: 'confidentialite', path: '/confidentialite' },
  { name: 'chatbot-deconnecte', path: '/chatbot' },
  { name: 'chatbot-vide', path: '/chatbot', auth: true },
  { name: 'chatbot-conversation', path: '/chatbot', auth: true, act: askQuestion },
  { name: 'chatbot-acces-en-attente', path: '/chatbot', auth: true, aiAccess: false, act: askQuestion },
  { name: 'aliment-frais-deconnecte', path: '/aliment-frais' },
  { name: 'aliment-frais', path: '/aliment-frais', auth: true },
  { name: 'aliment-frais-identification', path: '/aliment-frais', auth: true, vision: 'slow', act: uploadPhoto('.analyse-card[role=status]') },
  { name: 'aliment-frais-resultat', path: '/aliment-frais', auth: true, act: uploadPhoto('.analyse-recognised') },
  { name: 'aliment-frais-non-reconnu', path: '/aliment-frais', auth: true, vision: 'notFound', act: uploadPhoto('.capture-sheet, .analyse-card') },
];

for (const scenario of SCENARIOS) {
  test(scenario.name, async ({ page, isMobile }, testInfo) => {
    test.skip(Boolean(scenario.compactOnly) && testInfo.project.name.startsWith('desktop-'), 'menu mobile uniquement');
    await mockApi(page, scenario);
    await page.goto(scenario.path);
    await page.waitForLoadState('networkidle');
    if (scenario.act) await scenario.act(page);
    await page.evaluate(() => document.fonts.ready);
    // Scroll through the page once: images with loading="lazy" are only loaded when
    // they come near the screen, and a full-page screenshot does not scroll.
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 400) {
        window.scrollTo(0, y);
        await new Promise((resolve) => setTimeout(resolve, 30));
      }
      window.scrollTo(0, 0);
    });
    await page.waitForLoadState('networkidle');

    const overflow = await findOverflow(page);
    const axe = await runAxe(page);
    const inputFonts = isMobile ? await findSmallInputFonts(page) : [];
    const smallTargets = isMobile ? await findSmallTargets(page) : [];

    // Screenshot + findings, kept between runs (e2e/captures is git-ignored).
    const dir = new URL(`${testInfo.project.name}/`, CAPTURES_DIR);
    mkdirSync(dir, { recursive: true });
    const screenshot = await page.screenshot({ fullPage: true });
    writeFileSync(new URL(`${scenario.name}.png`, dir), screenshot);
    const findings = { page: scenario.name, path: scenario.path, overflow, axe, inputFonts, smallTargets };
    writeFileSync(new URL(`${scenario.name}.json`, dir), JSON.stringify(findings, null, 2));
    await testInfo.attach('capture', { body: screenshot, contentType: 'image/png' });

    for (const t of smallTargets) {
      testInfo.annotations.push({ type: 'cible tactile < 44 px', description: `${t.element} « ${t.text} » ${t.size}` });
    }

    expect.soft(overflow.elements, 'éléments qui dépassent de l’écran').toEqual([]);
    expect.soft(overflow.horizontalScroll, 'scroll horizontal').toBe(false);
    expect.soft(axe, 'violations axe (WCAG 2.2 AA)').toEqual([]);
    expect.soft(inputFonts, 'champs < 16 px (zoom automatique iOS)').toEqual([]);
  });
}