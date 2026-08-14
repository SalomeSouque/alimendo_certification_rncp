import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AnalyseZone from './AnalyseZone.jsx';

describe('AnalyseZone', () => {
  it('affiche la zone de dépôt au chargement, pas le spinner', () => {
    render(
      <MemoryRouter>
        <AnalyseZone dropzoneText="Déposer une photo" dropzoneHint="JPG, PNG" />
      </MemoryRouter>
    );

    // L'état initial montre le texte de dépôt passé en prop
    expect(screen.getByText('Déposer une photo')).toBeInTheDocument();

    // Et n'affiche PAS encore l'état de chargement
    expect(screen.queryByText(/Identification en cours/i)).not.toBeInTheDocument();
  });
});