// src/components/analyse/MobilePhotoCapture.jsx
// "Photo" tab (maquette M3b) and the "Aliment non reconnu" panel (M3e).
// The shutter opens the phone's own camera app (input capture="environment"):
// reliable on every phone, with its own flash and focus. A live camera inside
// the page is a possible improvement (V2).

import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import CaptureShell from './CaptureShell.jsx';
import ManualBarcodeForm from '../ManualBarcodeForm.jsx';
import { ImageIcon } from '../icons.jsx';
import { ACCEPTED_IMAGE_TYPES } from '../../services/vision';

const ACCEPT = ACCEPTED_IMAGE_TYPES.join(',');

/**
 * @param {{ analysis: ReturnType<import('../usePhotoAnalysis').usePhotoAnalysis> }} props
 *   status idle → capture screen; notFound / error → panel over the dimmed camera.
 */
export default function MobilePhotoCapture({ analysis }) {
  const { status, inputError, message, analyse, reset } = analysis;
  const failed = status === 'notFound' || status === 'error';
  const titleRef = useRef(null);

  // The panel title gets the focus, so the outcome is announced.
  useEffect(() => {
    if (failed) titleRef.current?.focus();
  }, [failed]);

  function handleFile(e) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (file) analyse(file);
  }

  const bottom = failed ? null : (
    <>
      <div className="capture-actions">
        <label className="capture-import">
          <span className="capture-import-icon"><ImageIcon /></span>
          <span aria-hidden="true">Importer</span>
          <input className="sr-only" type="file" accept={ACCEPT} aria-label="Importer une photo de l’aliment" onChange={handleFile} />
        </label>
        <label className="capture-shutter">
          <input
            className="sr-only"
            type="file"
            accept={ACCEPT}
            capture="environment"
            aria-label="Prendre une photo de l’aliment"
            onChange={handleFile}
          />
        </label>
        <span aria-hidden="true" />
      </div>
      {inputError && <p className="capture-error" role="alert">{inputError}</p>}
      <p className="capture-note">La photo est analysée puis oubliée : elle n’est jamais enregistrée.</p>
    </>
  );

  return (
    <>
      <CaptureShell tone="dark" title="Photographier un aliment" bottom={bottom} stageClassName="capture-stage--warm">
        {!failed && (
          <>
            <p className="capture-hint">Un seul aliment brut, non emballé : fruit, légume, viande ou poisson.</p>
            <div className="capture-frame" aria-hidden="true"><span /><span /><span /><span /></div>
            <p className="capture-sub">Touchez le déclencheur pour ouvrir l’appareil photo.</p>
          </>
        )}
      </CaptureShell>

      {failed && <div className="capture-sheet-backdrop" aria-hidden="true" />}
      {failed && (
        <section className="capture-sheet" aria-labelledby="sheet-title" role={status === 'error' ? 'alert' : undefined}>
          <div className="capture-sheet-icon"><img src="/assets/food_not_found.svg" alt="" aria-hidden="true" /></div>
          <h2 id="sheet-title" className="capture-sheet-title" ref={titleRef} tabIndex={-1}>
            {status === 'error' ? 'Analyse impossible pour le moment' : 'Aliment non reconnu'}
          </h2>
          <p className="capture-sheet-text">{message}</p>
          <button type="button" className="btn-primary" onClick={reset}>Réessayer</button>
          <Link to="/recherche" replace className="btn-secondary">Rechercher par nom</Link>
          <div className="or-sep">ou saisie manuelle</div>
          <ManualBarcodeForm showHint={false} />
          <p className="capture-sheet-note">Projet étudiant · cet outil ne remplace pas un suivi médical.</p>
        </section>
      )}
    </>
  );
}
