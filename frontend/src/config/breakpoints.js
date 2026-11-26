// src/config/breakpoints.js
// Widths where the layout changes structure (not only CSS).
// Keep in sync with the @media rules that use the same values.

/** Phones: full-screen analysis with bottom tabs (maquettes M3). */
export const MOBILE_QUERY = '(max-width: 767px)';

/** Phones and tablets: the desktop navigation does not fit, burger menu instead (maquette M1). */
export const COMPACT_HEADER_QUERY = '(max-width: 1023px)';
