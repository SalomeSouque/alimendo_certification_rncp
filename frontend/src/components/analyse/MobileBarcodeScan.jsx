// src/components/analyse/MobileBarcodeScan.jsx
// "Code-barre" tab (maquette M3a): the camera starts on its own and reads
// continuously, no button. Importer = photo of the barcode. Torch when the phone has one.

import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import CaptureShell from './CaptureShell.jsx';
import { useBarcodeScanner } from '../useBarcodeScanner';
import { FlashIcon, ImageIcon } from '../icons.jsx';

const NO_CAMERA =
  'La caméra n’est pas disponible dans ce navigateur. Importez une photo du code-barre, ou utilisez l’onglet « Écrire ».';

export default function MobileBarcodeScan() {
  const navigate = useNavigate();
  const {
    status, error, videoRef, cameraAvailable, cameraOn, start, readFile,
    torchAvailable, torchOn, toggleTorch,
  } = useBarcodeScanner((code) => navigate(`/produit/${code}`));
  const fileRef = useRef(null);

  // Continuous reading: the camera opens with the tab (maquette M3a).
  const startRef = useRef(start);
  useEffect(() => {
    if (cameraAvailable) startRef.current();
  }, [cameraAvailable]);

  async function handleFile(e) {
    await readFile(e.target.files?.[0]);
    if (fileRef.current) fileRef.current.value = '';
  }

  const torch = torchAvailable ? (
    <button
      type="button"
      className="capture-round capture-round--right"
      aria-label="Lampe torche"
      aria-pressed={torchOn}
      onClick={toggleTorch}
    >
      <FlashIcon />
    </button>
  ) : null;

  const bottom = (
    <>
      <div className="capture-actions capture-actions--left">
        <label className="capture-import">
          <span className="capture-import-icon"><ImageIcon /></span>
          <span aria-hidden="true">Importer</span>
          <input
            ref={fileRef}
            className="sr-only"
            type="file"
            accept="image/*"
            aria-label="Importer une photo du code-barre"
            onChange={handleFile}
            disabled={status === 'decoding'}
          />
        </label>
        <p className="capture-status" role="status">
          {status === 'scanning' && <><span className="capture-dot" aria-hidden="true" />Lecture automatique…</>}
          {status === 'starting' && 'Ouverture de la caméra…'}
          {status === 'decoding' && 'Lecture du code-barre…'}
        </p>
      </div>
      {error && <p className="capture-error" role="alert">{error}</p>}
      <p className="capture-note">L’image reste sur votre appareil : seuls les chiffres du code-barre sont utilisés.</p>
    </>
  );

  return (
    <CaptureShell tone="dark" title="Scanner un code-barre" topRight={torch} bottom={bottom}>
      {/* The video element must exist (and be displayed) before the camera starts. */}
      <video
        ref={videoRef}
        className="capture-video"
        muted
        playsInline
        aria-label="Aperçu de la caméra"
        hidden={!cameraOn}
      />

      {cameraAvailable ? (
        <>
          <p className="capture-hint">Placez le code-barre dans le cadre</p>
          <div className="capture-frame capture-frame--barcode" aria-hidden="true">
            <span /><span /><span /><span />
            {status === 'scanning' && <div className="capture-scanline" />}
          </div>
          {!cameraOn && status !== 'decoding' && (
            <button type="button" className="btn-secondary" onClick={start}>
              Relancer la caméra
            </button>
          )}
        </>
      ) : (
        <p className="capture-message">{NO_CAMERA}</p>
      )}
    </CaptureShell>
  );
}
