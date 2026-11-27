// src/components/Wave.jsx
// Decorative yellow line behind a page. <picture>: the phone gets its own drawing
// (another shape, positioned in the page CSS) and downloads only that one.

import { MOBILE_QUERY } from '../config/breakpoints';
import { useMediaQuery } from './useMediaQuery';

/**
 * @param {{ desktop: string, mobile: string, className: string, mobileMedia?: string,
 *   hiddenMedia?: string }} props
 *   className positions the line (e.g. "wave-auth"), for each width, in the page CSS;
 *   mobileMedia: up to which width the mobile drawing is used (phones by default);
 *   hiddenMedia: widths where neither drawing fits (the cut ends of the phone drawing
 *   would show): no line there.
 */
export default function Wave({ desktop, mobile, className, mobileMedia = MOBILE_QUERY, hiddenMedia }) {
  const hidden = useMediaQuery(hiddenMedia ?? '(max-width: 0px)'); // never matches
  if (hidden) return null;
  return (
    <picture>
      <source media={mobileMedia} srcSet={mobile} />
      <img className={`wave ${className}`} src={desktop} alt="" aria-hidden="true" />
    </picture>
  );
}