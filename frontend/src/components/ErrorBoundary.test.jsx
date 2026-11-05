import { render, screen } from '@testing-library/react';
import ErrorBoundary from './ErrorBoundary';

function Broken() {
  throw new Error('boom');
}

it('shows a message instead of a blank page when a child crashes', () => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  render(<ErrorBoundary><Broken /></ErrorBoundary>);
  expect(screen.getByRole('alert')).toHaveTextContent('Une erreur est survenue');
  expect(screen.getByRole('button', { name: 'Recharger la page' })).toBeInTheDocument();
});
