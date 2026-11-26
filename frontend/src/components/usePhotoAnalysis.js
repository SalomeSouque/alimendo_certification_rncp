// src/components/usePhotoAnalysis.js
// Photo analysis state, shared by the desktop drop zone (AnalyseZone) and the
// mobile capture screen (MobilePhotoCapture).
// States: idle | loading | result (recognised food) | notFound | error | pending (403).

import { useEffect, useState } from 'react';
import { identifyFood, validateImage, VISION_STATUS } from '../services/vision';

export function usePhotoAnalysis() {
  const [status, setStatus] = useState('idle');
  const [inputError, setInputError] = useState(null);
  const [message, setMessage] = useState(null);
  const [result, setResult] = useState(null);
  const [preview, setPreview] = useState(null);

  // Free the preview URL when it changes or when the component unmounts.
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  /** Checks the file, then sends it to POST /ai/vision. */
  async function analyse(file) {
    if (!file) return;
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
      if (err?.status === 403) {
        setStatus('pending'); // AI access not approved yet by an admin
        return;
      }
      setMessage(err?.message ?? 'Une erreur est survenue. Réessayez.');
      setStatus('error');
    }
  }

  function reset() {
    setStatus('idle');
    setResult(null);
    setMessage(null);
    setPreview(null);
    setInputError(null);
  }

  return { status, inputError, message, result, preview, analyse, reset };
}
