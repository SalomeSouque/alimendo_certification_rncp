// e2e/support/checks.js
// Measurable responsive / accessibility checks, run inside the real page.

import AxeBuilder from '@axe-core/playwright';

// WCAG 2.2 level AA (axe also includes target-size, 2.5.8, with the wcag22aa tag).
const AXE_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

// Comfortable touch target (Apple / Material guidance). Below it: warning only,
// the AA failure threshold (24 px) is checked by axe.
const COMFORT_TARGET_PX = 44;

// Below 16 px, iOS Safari zooms the page when the field gets the focus.
const MIN_INPUT_FONT_PX = 16;

/**
 * Elements that stick out of the viewport horizontally (cut off or causing a scrollbar).
 * Only the outermost offending element is kept: it is usually the cause.
 * Ignored on purpose: `.wave` (decorative yellow line), `.sr-only`, and `[data-bleed]`
 * (an element the design cuts at the screen edge on purpose; the page must still not scroll).
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<{ horizontalScroll: boolean, elements: object[] }>}
 */
export function findOverflow(page) {
  return page.evaluate(() => {
    const viewport = document.documentElement.clientWidth;
    const offenders = new Set();
    for (const el of document.body.querySelectorAll('*')) {
      if (el.closest('.wave, .sr-only, [data-bleed]')) continue;
      const style = getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden') continue;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      if (r.right > viewport + 1 || r.left < -1) offenders.add(el);
    }
    const elements = [...offenders]
      .filter((el) => !offenders.has(el.parentElement))
      .map((el) => {
        const r = el.getBoundingClientRect();
        return {
          element: `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ''}${[...el.classList].map((c) => `.${c}`).join('')}`,
          text: (el.textContent ?? '').trim().replace(/\s+/g, ' ').slice(0, 60),
          left: Math.round(r.left),
          right: Math.round(r.right),
          viewport,
        };
      });
    // Real scroll test: scrollWidth also counts content hidden by `overflow-x: clip`,
    // so we try to scroll and check whether the page actually moved.
    const y = window.scrollY;
    window.scrollTo(10000, y);
    document.body.scrollLeft = 10000;
    const horizontalScroll = window.scrollX > 0 || document.body.scrollLeft > 0;
    window.scrollTo(0, y);
    document.body.scrollLeft = 0;
    return { horizontalScroll, elements };
  });
}

/**
 * Form fields whose font is smaller than 16 px (iOS auto-zoom on focus).
 * @param {import('@playwright/test').Page} page
 */
export function findSmallInputFonts(page) {
  return page.evaluate((min) => {
    return [...document.querySelectorAll('input:not([type=hidden]):not([type=file]):not([type=checkbox]):not([type=radio]), select, textarea')]
      .filter((el) => el.getBoundingClientRect().width > 1)
      .map((el) => ({
        element: `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ''}[placeholder="${el.placeholder ?? ''}"]`,
        fontSize: parseFloat(getComputedStyle(el).fontSize),
      }))
      .filter((f) => f.fontSize < min);
  }, MIN_INPUT_FONT_PX);
}

/**
 * Interactive elements smaller than 44 px on one side (warning, not a WCAG failure).
 * Links inside a sentence (display: inline) are exempt, as in WCAG 2.5.8.
 * @param {import('@playwright/test').Page} page
 */
export function findSmallTargets(page) {
  return page.evaluate((min) => {
    const selector = 'a[href], button, select, [role=button], [role=switch], label.dropzone';
    return [...document.querySelectorAll(selector)]
      .filter((el) => !el.closest('.sr-only'))
      .filter((el) => getComputedStyle(el).display !== 'inline')
      .map((el) => ({ el, r: el.getBoundingClientRect() }))
      .filter(({ r }) => r.width > 0 && r.height > 0 && (r.width < min || r.height < min))
      .map(({ el, r }) => ({
        element: `${el.tagName.toLowerCase()}${[...el.classList].map((c) => `.${c}`).join('')}`,
        text: (el.textContent || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 40),
        size: `${Math.round(r.width)}×${Math.round(r.height)}`,
      }));
  }, COMFORT_TARGET_PX);
}

/**
 * axe-core analysis, reduced to what is useful in a report.
 * @param {import('@playwright/test').Page} page
 */
export async function runAxe(page) {
  const { violations } = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
  return violations.map((v) => ({
    rule: v.id,
    impact: v.impact,
    help: v.help,
    helpUrl: v.helpUrl,
    elements: v.nodes.map((n) => n.target.join(' ')).slice(0, 10),
  }));
}
