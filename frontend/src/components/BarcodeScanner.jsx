// src/components/BarcodeScanner.jsx
// Desktop / tablet: two ways to read a barcode without typing it, live camera or a photo.
// Calls onCode(code) with a valid 8–14 digit code. Logic in useBarcodeScanner.

import { useId, useRef } from 'react';
import { useBarcodeScanner } from './useBarcodeScanner';
import './BarcodeScanner.css';

export default function BarcodeScanner({ onCode }) {
  const { status, error, videoRef, cameraAvailable, cameraOn, start, cancel, readFile } = useBarcodeScanner(onCode);
  const fileRef = useRef(null);
  const statusId = useId();

  async function handleFile(e) {
    await readFile(e.target.files?.[0]);
    if (fileRef.current) fileRef.current.value = '';
  }

  return (
    <div className="scanner">
      {/* The video element must exist before the camera starts. */}
      <div className={`scanner-preview${cameraOn ? '' : ' scanner-preview--hidden'}`}>
        <video ref={videoRef} className="scanner-video" muted playsInline aria-label="Aperçu de la caméra" />
        <div className="scanner-frame" aria-hidden="true" />
      </div>

      <p id={statusId} className="scanner-status" role="status">
        {status === 'starting' && 'Ouverture de la caméra…'}
        {status === 'scanning' && 'Visez le code-barre : la lecture est automatique.'}
        {status === 'decoding' && 'Lecture du code-barre…'}
      </p>

      <div className="scanner-actions">
        {cameraOn ? (
          <button type="button" className="btn-secondary" onClick={cancel}>
            Arrêter la caméra
          </button>
        ) : (
          cameraAvailable && (
            <button type="button" className="btn-primary" onClick={start} disabled={status === 'decoding'}>
              Scanner avec la caméra
            </button>
          )
        )}

        {!cameraOn && (
          <label className="btn-secondary scanner-file">
            Importer une photo du code-barre
            <input
              ref={fileRef}
              className="sr-only"
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFile}
              disabled={status === 'decoding'}
            />
          </label>
        )}
      </div>

      {error && <p className="scanner-error" role="alert">{error}</p>}
      <p className="scanner-note">L’image reste sur votre appareil : seuls les chiffres du code-barre sont utilisés.</p>
    </div>
  );
}
