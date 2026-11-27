// Decorative line: phone drawing, desktop drawing, or none where neither fits.
import { render } from '@testing-library/react';
import { mockViewport } from '../test/viewport';
import Wave from './Wave';

const props = {
  className: 'wave-auth',
  desktop: '/desktop.svg',
  mobile: '/mobile.webp',
  mobileMedia: '(max-width: 420px)',
  hiddenMedia: '(min-width: 421px) and (max-width: 767px)',
};

describe('Wave', () => {
  it('phone: the phone drawing is offered for the phone widths', () => {
    mockViewport(360);
    const { container } = render(<Wave {...props} />);
    expect(container.querySelector('source')).toHaveAttribute('media', '(max-width: 420px)');
    expect(container.querySelector('img.wave-auth')).toHaveAttribute('aria-hidden', 'true');
  });

  it('between the two drawings: no line at all', () => {
    mockViewport(600);
    const { container } = render(<Wave {...props} />);
    expect(container.querySelector('img')).toBeNull();
  });

  it('without hiddenMedia, the line is always there (desktop by default in jsdom)', () => {
    const { container } = render(<Wave className="wave-savoir" desktop="/d.svg" mobile="/m.webp" />);
    expect(container.querySelector('img.wave-savoir')).toHaveAttribute('src', '/d.svg');
  });
});
