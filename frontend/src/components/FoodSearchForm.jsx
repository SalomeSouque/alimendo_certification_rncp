// src/components/FoodSearchForm.jsx
// Search-by-name form shared by the Analyser and Search pages.
// It only navigates to /recherche?q=…; the Search page calls the API.

import { useId, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './FoodSearchForm.css';
import { SEARCH_MAX_LENGTH, SEARCH_MIN_LENGTH } from '../services/score';

export default function FoodSearchForm({ initialTerm = '', placeholder = 'Rechercher un aliment par nom' }) {
  const [term, setTerm] = useState(initialTerm);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const errorId = useId();

  function handleSubmit(e) {
    e.preventDefault();
    const clean = term.trim();
    if (clean.length < SEARCH_MIN_LENGTH) {
      setError(`Saisissez au moins ${SEARCH_MIN_LENGTH} caractères.`);
      return;
    }
    setError(null);
    navigate(`/recherche?${new URLSearchParams({ q: clean })}`);
  }

  return (
    <div className="search-block">
      <form className="search-bar" role="search" onSubmit={handleSubmit} noValidate>
        <img className="loupe" src="/assets/loupe.svg" alt="" aria-hidden="true" />
        <input
          type="search"
          placeholder={placeholder}
          aria-label="Rechercher un aliment par nom"
          maxLength={SEARCH_MAX_LENGTH}
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
        />
        <button className="search-go" type="submit" aria-label="Rechercher">
          <img src="/assets/fleche_recherche_ou_retour.svg" alt="" aria-hidden="true" />
        </button>
      </form>
      {error && <p id={errorId} className="search-error">{error}</p>}
    </div>
  );
}
