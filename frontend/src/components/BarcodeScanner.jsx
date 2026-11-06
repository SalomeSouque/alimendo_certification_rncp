// src/components/BarcodeScanner.jsx
// Two ways to read a barcode without typing it: live camera, or a photo.
// Calls onCode(code) with a valid 8–14 digit code.

import { useEffect, useId, useRef, useState } from 'react';
import {
  cameraErrorMessage,
  decodeBarcodeFromFile,
  isCameraSupported,
  startCameraScan,
} from '../services/barcode';
import './BarcodeScanner.css';

export default function BarcodeScanner({ onCode }) {
  // idle | starting | scanning | decoding
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);
  const videoRef = useRef(null);
  const controlsRef = useRef(null);
  const fileRef = useRef(null);
  const statusId = useId();
  // Latest callback, without restarting the camera when the parent re-renders.
  const onCodeRef = useRef(onCode);
  useEffect(() => { onCodeRef.current = onCode; }, [onCode]);
  const cameraAvailable = isCameraSupported();

  function stopCamera() {
    controlsRef.current?.stop();
    controlsRef.current = null;
  }

  // Always release the camera when leaving the page.
  useEffect(() => stopCamera, []);

  // The camera starts once the preview is displayed: some browsers do not
  // play a video that is hidden (display: none) when it receives its stream.
  useEffect(() => {
    if (status !== 'starting') return undefined;
    let cancelled = false;
    startCameraScan(
      videoRef.current,
      (code) => {
        controlsRef.current = null;
        setStatus('idle');
        onCodeRef.current(code);
      },
      (err) => {
        console.error('Barcode scan stopped:', err);
        controlsRef.current = null;
        setStatus('idle');
        setError(cameraErrorMessage(err));
      },
    )
      .then((controls) => {
        if (cancelled) {
          controls.stop();
          return;
        }
        controlsRef.current = controls;
        setStatus('scanning');
      })
      .catch((err) => {
        // Kept in the console to diagnose a camera that does not start.
        console.error('Barcode camera error:', err);
        if (cancelled) return;
        setStatus('idle');
        setError(cameraErrorMessage(err));
      });
    return () => { cancelled = true; };
  }, [status]);

  function startCamera() {
    setError(null);
    setStatus('starting');
  }

  function cancelCamera() {
    stopCamera();
    setStatus('idle');
  }

  async function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setStatus('decoding');
    const code = await decodeBarcodeFromFile(file);
    setStatus('idle');
    if (fileRef.current) fileRef.current.value = '';
    if (code) {
      onCodeRef.current(code);
    } else {
      setError('Aucun code-barre lisible sur cette photo. Cadrez-le de plus près, bien net et éclairé, ou saisissez les chiffres.');
    }
  }

  const cameraOn = status === 'starting' || status === 'scanning';

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
          <button type="button" className="btn-secondary" onClick={cancelCamera}>
            Arrêter la caméra
          </button>
        ) : (
          cameraAvailable && (
            <button type="button" className="btn-primary" onClick={startCamera} disabled={status === 'decoding'}>
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