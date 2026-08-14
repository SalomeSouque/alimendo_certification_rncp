import { useState } from 'react';
import { Link } from 'react-router-dom';
import './AnalyseZone.css';

export default function AnalyseZone({ dropzoneText, dropzoneHint }) {
  // 'idle' = zone de dépôt | 'loading' = analyse en cours | 'not_found' = aliment non reconnu
  const [status, setStatus] = useState('idle');

  function handleFile(e) {
    if (!e.target.files || e.target.files.length === 0) return;
    setStatus('loading');
    // Placeholder du futur appel API (VLM / Open Food Facts).
    // Pour la démo : on simule une analyse qui n'aboutit pas.
    setTimeout(() => setStatus('not_found'), 2500);
  }

  if (status === 'loading') {
    return (
      <div className="analyse-card">
        <div className="spinner" role="status" aria-label="Analyse en cours"></div>
        <div className="analyse-card-title">Identification en cours…</div>
        <p className="analyse-card-text">
          L'analyse de la photo prend en général quelques dizaines de secondes.
          Vous pouvez laisser cette page ouverte.
        </p>
      </div>
    );
  }

  if (status === 'not_found') {
    return (
      <div className="analyse-card">
        <img className="analyse-card-icon" src="/assets/food_not_found.svg" alt="" />
        <div className="analyse-card-title">Aliment non reconnu</div>
        <p className="analyse-card-text">
          La photo n'a pas permis d'identifier l'aliment.{' '}
          <button type="button" className="link-btn" onClick={() => setStatus('idle')}>
            Réessayer
          </button>{' '}
          ou <Link to="/analyser">rechercher par nom</Link>.
        </p>
      </div>
    );
  }

  // status === 'idle'
  return (
    <label className="dropzone">
      <input type="file" accept="image/png,image/jpeg" hidden onChange={handleFile} />
      <img className="up" src="/assets/transfert.svg" alt="" />
      <div className="main">{dropzoneText}</div>
      <div className="hint">{dropzoneHint}</div>
    </label>
  );
}