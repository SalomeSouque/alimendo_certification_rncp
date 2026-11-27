// src/components/AnalyseZone.jsx
// Photo analysis: drop zone → checks → POST /ai/vision → result.
// The state lives in usePhotoAnalysis; pass `analysis` to share it with a parent
// (the mobile page switches between this zone and the full-screen capture).

import { useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import FoodScore from './FoodScore.jsx';
import AccessPending from './AccessPending.jsx';
import { usePhotoAnalysis } from './usePhotoAnalysis';
import { ACCEPTED_IMAGE_TYPES } from '../services/vision';
import './AnalyseZone.css';

/** "Identification en cours…" card (maquette M3f). */
export function AnalyseLoading({ preview }) {
  return (
    <div className="analyse-card" role="status">
      {preview && <img className="analyse-preview" src={preview} alt="Photo envoyée" />}
      <div className="spinner" aria-hidden="true" />
      <p className="analyse-card-title">Identification en cours…</p>
      <p className="analyse-card-text">
        L’analyse de la photo peut prendre jusqu’à une trentaine de secondes.
        Vous pouvez laisser cette page ouverte.
      </p>
    </div>
  );
}

/** Recognised food: label + score (maquette M3g). Focus moves to it. */
export function AnalyseResult({ result, onReset }) {
  const ref = useRef(null);
  useEffect(() => { ref.current?.focus(); }, []);
  return (
    <div className="analyse-result">
      <div className="analyse-recognised" ref={ref} tabIndex={-1}>
        <p>
          Aliment identifié sur la photo : <strong>{result.label_identifie}</strong>
        </p>
        <p className="analyse-recognised-actions">
          Ce n’est pas le bon aliment ? <Link to="/recherche">Rechercher par nom</Link>
          {' · '}
          <button type="button" className="link-btn" onClick={onReset}>Analyser une autre photo</button>
        </p>
      </div>
      <FoodScore detail={result.resultat} titleLevel={2} />
    </div>
  );
}

export default function AnalyseZone({ dropzoneText, dropzoneHint, analysis }) {
  const own = usePhotoAnalysis();
  const { status, inputError, message, result, preview, analyse, reset } = analysis ?? own;
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);
  const outcomeRef = useRef(null);
  const hintId = useId();
  const errorId = useId();

  // Move focus to the outcome so keyboard and screen reader users get it.
  useEffect(() => {
    if (status === 'notFound' || status === 'error') outcomeRef.current?.focus();
  }, [status]);

  function handleReset() {
    reset();
    if (inputRef.current) inputRef.current.value = '';
  }

  function handleChange(e) {
    const file = e.target.files?.[0];
    if (file) analyse(file);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) analyse(file);
  }

  if (status === 'loading') return <AnalyseLoading preview={preview} />;
  if (status === 'pending') return <AccessPending />;
  if (status === 'result') return <AnalyseResult result={result} onReset={handleReset} />;

  if (status === 'notFound' || status === 'error') {
    return (
      <div className="analyse-card" ref={outcomeRef} tabIndex={-1} role={status === 'error' ? 'alert' : undefined}>
        <img className="analyse-card-icon" src="/assets/food_not_found.svg" alt="" aria-hidden="true" />
        <h2 className="analyse-card-title">
          {status === 'error' ? 'Analyse impossible pour le moment' : 'Aliment non reconnu'}
        </h2>
        <p className="analyse-card-text">{message}</p>
        <div className="analyse-card-actions">
          <button type="button" className="btn-primary" onClick={handleReset}>Réessayer avec une photo</button>
          <Link to="/recherche" className="btn-secondary">Rechercher par nom</Link>
        </div>
      </div>
    );
  }

  // status === 'idle'
  return (
    <div className="dropzone-wrap">
      <label
        className={`dropzone${dragging ? ' dropzone--active' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        {/* Visually hidden but focusable: the label is the visible control. */}
        <input
          ref={inputRef}
          className="sr-only"
          type="file"
          accept={ACCEPTED_IMAGE_TYPES.join(',')}
          onChange={handleChange}
          aria-describedby={[hintId, inputError ? errorId : null].filter(Boolean).join(' ')}
          aria-invalid={Boolean(inputError)}
        />
        <img className="up" src="/assets/transfert.svg" alt="" aria-hidden="true" />
        <span className="main">{dropzoneText}</span>
        <span className="hint" id={hintId}>{dropzoneHint}</span>
      </label>
      {inputError && <p id={errorId} className="dropzone-error" role="alert">{inputError}</p>}
    </div>
  );
}
