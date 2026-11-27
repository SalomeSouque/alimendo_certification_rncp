// src/config/breakpoints.js
// Widths where the layout changes structure (not only CSS).
// Keep in sync with the @media rules that use the same values.

/** Phones: full-screen analysis with bottom tabs (maquettes M3). */
export const MOBILE_QUERY = '(max-width: 767px)';

/** Phones, tablets and small laptops: the desktop navigation is cramped and the home
 *  composition does not fit below 1280 px, burger menu and one-column home instead. */
export const COMPACT_HEADER_QUERY = '(max-width: 1279px)';