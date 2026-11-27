// src/components/ManualBarcodeForm.jsx
// Typed barcode: validates the EAN (8–14 digits), then opens /produit/:code.
// Used on the packaged product page, the "Écrire" tab and the "not recognised" panel.

import { useId, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BARCODE_PATTERN } from '../services/score';
import './ManualBarcodeForm.css';

/** @param {{ showHint?: boolean }} props */
export default function ManualBarcodeForm({ showHint = true }) {
  const [code, setCode] = useState('');
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const inputId = useId();
  const hintId = useId();
  const errorId = useId();

  function handleSubmit(e) {
    e.preventDefault();
    const clean = code.replace(/\s/g, '');
    if (!BARCODE_PATTERN.test(clean)) {
      setError('Le code-barre doit contenir entre 8 et 14 chiffres, sans lettres.');
      inputRef.current?.focus();
      return;
    }
    setError(null);
    navigate(`/produit/${clean}`);
  }

  const describedBy = [showHint ? hintId : null, error ? errorId : null].filter(Boolean).join(' ');

  return (
    <>
      <form className="manual" onSubmit={handleSubmit} noValidate>
        <label htmlFor={inputId} className="sr-only">Code-barre</label>
        <input
          id={inputId}
          ref={inputRef}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          placeholder="Ex : 3760049790337"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy || undefined}
        />
        <button type="submit" className="btn-primary">Valider</button>
      </form>
      {showHint && (
        <p id={hintId} className="emb-hint">8 à 14 chiffres. Données produit issues d’Open Food Facts.</p>
      )}
      {error && <p id={errorId} className="emb-error">{error}</p>}
    </>
  );
}
