// src/config/breakpoints.js
// Widths where the layout changes structure (not only CSS).
// Keep in sync with the @media rules that use the same values.

/** Phones: full-screen analysis with bottom tabs (maquettes M3). */
export const MOBILE_QUERY = '(max-width: 767px)';

/** Phones, tablets and small laptops: the desktop navigation is cramped and the home
 *  composition does not fit below 1280 px, burger menu and one-column home instead. */
export const COMPACT_HEADER_QUERY = '(max-width: 1279px)';

/** Home page layouts (Home.jsx, Home.css). One column with the phone maquette up to
 *  859 px; tablet composition from 860 to 1279 px; desktop maquette from 1280 px.
 *  The tablet composition is drawn at 1024 px and zoomed: below 860 px (zoom < 0.84)
 *  the minimum text size would make the paragraphs run into the line. */
export const HOME_ONE_COLUMN_QUERY = '(max-width: 859px)';
export const HOME_TABLET_QUERY = '(min-width: 860px) and (max-width: 1279px)';

/** Home: the phone line pieces are cut where the line leaves a phone screen; above
 *  460 px their cut ends would show, so the line is not displayed. */
export const HOME_PHONE_LINE_QUERY = '(max-width: 460px)';