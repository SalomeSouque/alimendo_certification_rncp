// src/components/useBarcodeScanner.js
// Barcode reading logic shared by the desktop scanner (BarcodeScanner) and the
// full-screen mobile scan (MobileBarcodeScan): live camera, photo, torch, errors.

import { useEffect, useRef, useState } from 'react';
import {
  cameraErrorMessage,
  decodeBarcodeFromFile,
  isCameraSupported,
  startCameraScan,
} from '../services/barcode';

export const PHOTO_NOT_READABLE =
  'Aucun code-barre lisible sur cette photo. Cadrez-le de plus près, bien net et éclairé, ou saisissez les chiffres.';

/**
 * @param {(code: string) => void} onCode - called once with a valid 8–14 digit code
 * @returns {{
 *   status: 'idle'|'starting'|'scanning'|'decoding', error: string|null,
 *   videoRef: object, cameraAvailable: boolean, cameraOn: boolean,
 *   start: () => void, cancel: () => void, readFile: (file: File) => Promise<void>,
 *   torchAvailable: boolean, torchOn: boolean, toggleTorch: () => void,
 * }}
 */
export function useBarcodeScanner(onCode) {
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);
  const [torchAvailable, setTorchAvailable] = useState(false);
  const [torchOn, setTorchOn] = useState(false);
  const videoRef = useRef(null);
  const controlsRef = useRef(null);
  // Latest callback, without restarting the camera when the parent re-renders.
  const onCodeRef = useRef(onCode);
  useEffect(() => { onCodeRef.current = onCode; }, [onCode]);
  const cameraAvailable = isCameraSupported();

  function stopCamera() {
    controlsRef.current?.stop();
    controlsRef.current = null;
    setTorchAvailable(false);
    setTorchOn(false);
  }

  // Always release the camera when leaving the page.
  useEffect(() => () => controlsRef.current?.stop(), []);

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
        setTorchAvailable(Boolean(controls.setTorch));
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

  function start() {
    setError(null);
    setStatus('starting');
  }

  function cancel() {
    stopCamera();
    setStatus('idle');
  }

  async function readFile(file) {
    if (!file) return;
    stopCamera();
    setError(null);
    setStatus('decoding');
    const code = await decodeBarcodeFromFile(file);
    setStatus('idle');
    if (code) {
      onCodeRef.current(code);
    } else {
      setError(PHOTO_NOT_READABLE);
    }
  }

  function toggleTorch() {
    const setTorch = controlsRef.current?.setTorch;
    if (!setTorch) return;
    const next = !torchOn;
    setTorch(next)
      .then(() => setTorchOn(next))
      .catch((err) => console.error('Torch error:', err));
  }

  return {
    status,
    error,
    videoRef,
    cameraAvailable,
    cameraOn: status === 'starting' || status === 'scanning',
    start,
    cancel,
    readFile,
    torchAvailable,
    torchOn,
    toggleTorch,
  };
}
