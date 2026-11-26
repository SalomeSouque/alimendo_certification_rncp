// src/components/Wave.jsx
// Decorative yellow line behind a page. <picture>: the phone gets its own drawing
// (another shape, positioned in the page CSS) and downloads only that one.

import { MOBILE_QUERY } from '../config/breakpoints';

/**
 * @param {{ desktop: string, mobile: string, className: string, mobileMedia?: string }} props
 *   className positions the line (e.g. "wave-home"), for each width, in the page CSS;
 *   mobileMedia: up to which width the mobile drawing is used (phones by default).
 */
export default function Wave({ desktop, mobile, className, mobileMedia = MOBILE_QUERY }) {
  return (
    <picture>
      <source media={mobileMedia} srcSet={mobile} />
      <img className={`wave ${className}`} src={desktop} alt="" aria-hidden="true" />
    </picture>
  );
}
