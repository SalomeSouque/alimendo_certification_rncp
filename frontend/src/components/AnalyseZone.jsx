// src/components/AnalyseZone.jsx
// Photo analysis: drop zone → checks → POST /ai/vision → result.
// States: idle | loading | result (recognised food) | notFound | error.

import { useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import FoodScore from './FoodScore.jsx';
import { identifyFood, validateImage, VISION_STATUS, ACCEPTED_IMAGE_TYPES } from '../services/vision';
import './AnalyseZone.css';

export default function AnalyseZone({ dropzoneText, dropzoneHint }) {
  const [status, setStatus] = useState('idle');
  const [inputError, setInputError] = useState(null);
  const [message, setMessage] = useState(null);
  const [result, setResult] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);
  const resultRef = useRef(null);
  const hintId = useId();
  const errorId = useId();

  // Free the preview URL when it changes or when the component unmounts.
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  // Move focus to the outcome so keyboard and screen reader users get it.
  useEffect(() => {
    if (status !== 'idle' && status !== 'loading') resultRef.current?.focus();
  }, [status]);

  async function analyse(file) {
    const error = validateImage(file);
    if (error) {
      setInputError(error);
      return;
    }
    setInputError(null);
    setPreview(URL.createObjectURL(file));
    setStatus('loading');
    try {
      const response = await identifyFood(file);
      if (response.statut === VISION_STATUS.RECOGNIZED && response.resultat) {
        setResult(response);
        setStatus('result');
      } else {
        setMessage(response.message ?? 'La photo n’a pas permis d’identifier l’aliment.');
        setStatus('notFound');
      }
    } catch (err) {
      if (err?.status === 401) return; // central redirect to /connexion
      setMessage(err?.message ?? 'Une erreur est survenue. Réessayez.');
      setStatus('error');
    }
  }

  function reset() {
    setStatus('idle');
    setResult(null);
    setMessage(null);
    setPreview(null);
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

  if (status === 'loading') {
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

  if (status === 'result') {
    return (
      <div className="analyse-result">
        <div className="analyse-recognised" ref={resultRef} tabIndex={-1}>
          <p>
            Aliment identifié sur la photo : <strong>{result.label_identifie}</strong>
          </p>
          <p className="analyse-recognised-actions">
            Ce n’est pas le bon aliment ? <Link to="/analyser">Rechercher par nom</Link>
            {' · '}
            <button type="button" className="link-btn" onClick={reset}>Analyser une autre photo</button>
          </p>
        </div>
        <FoodScore detail={result.resultat} titleLevel={2} />
      </div>
    );
  }

  if (status === 'notFound' || status === 'error') {
    return (
      <div className="analyse-card" ref={resultRef} tabIndex={-1} role={status === 'error' ? 'alert' : undefined}>
        <img className="analyse-card-icon" src="/assets/food_not_found.svg" alt="" aria-hidden="true" />
        <h2 className="analyse-card-title">
          {status === 'error' ? 'Analyse impossible pour le moment' : 'Aliment non reconnu'}
        </h2>
        <p className="analyse-card-text">{message}</p>
        <div className="analyse-card-actions">
          <button type="button" className="btn-primary" onClick={reset}>Réessayer avec une photo</button>
          <Link to="/analyser" className="btn-secondary">Rechercher par nom</Link>
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