import { render, screen, act } from '@testing-library/react';
import { vi } from 'vitest';
import Toast from './Toast';

describe('Toast', () => {
  it('announces the message and dismisses itself after the duration', () => {
    vi.useFakeTimers();
    const onDismiss = vi.fn();
    render(<Toast toast={{ id: 1, text: 'Accès ouvert pour lea@exemple.fr' }} onDismiss={onDismiss} duration={1000} />);

    expect(screen.getByRole('status')).toHaveTextContent('Accès ouvert pour lea@exemple.fr');
    act(() => { vi.advanceTimersByTime(999); });
    expect(onDismiss).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(1); });
    expect(onDismiss).toHaveBeenCalledOnce();
    vi.useRealTimers();
  });

  it('no toast: keeps an empty live region', () => {
    render(<Toast toast={null} onDismiss={() => {}} />);
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
  });
});
