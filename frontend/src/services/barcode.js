// src/services/barcode.js
// Barcode reading in the browser (ZXing). Nothing is sent to a server:
// the image or the camera stream stays on the device, only the digits are
// used afterwards (GET /score/code-barre/{code}).
// The library is loaded on demand so it does not weigh on the other pages.

import { BARCODE_PATTERN } from './score';

/** Formats printed on food packaging. */
async function createReader() {
  const [{ BrowserMultiFormatOneDReader }, { BarcodeFormat, DecodeHintType }] = await Promise.all([
    import('@zxing/browser'),
    import('@zxing/library'),
  ]);
  const hints = new Map([
    [DecodeHintType.POSSIBLE_FORMATS, [BarcodeFormat.EAN_13, BarcodeFormat.EAN_8, BarcodeFormat.UPC_A, BarcodeFormat.UPC_E]],
    [DecodeHintType.TRY_HARDER, true],
  ]);
  return new BrowserMultiFormatOneDReader(hints);
}

/** Keeps only codes the API accepts (8 to 14 digits). */
function cleanCode(text) {
  const code = String(text ?? '').replace(/\s/g, '');
  return BARCODE_PATTERN.test(code) ? code : null;
}

/** True when the browser can open a camera (secure context + API available). */
export function isCameraSupported() {
  return Boolean(window.isSecureContext && navigator.mediaDevices?.getUserMedia);
}

/**
 * Reads a barcode on a photo.
 * @param {File} file
 * @returns {Promise<string|null>} the code, or null when none is readable.
 */
export async function decodeBarcodeFromFile(file) {
  const reader = await createReader();
  const url = URL.createObjectURL(file);
  try {
    const result = await reader.decodeFromImageUrl(url);
    return cleanCode(result?.getText());
  } catch {
    return null; // NotFoundException: no barcode found on the image
  } finally {
    URL.revokeObjectURL(url);
  }
}

/**
 * Starts the back camera and calls onCode once with the first valid code.
 * @param {HTMLVideoElement} video - preview element
 * @param {(code: string) => void} onCode
 * @returns {Promise<{ stop: () => void }>} controls, to stop the camera
 * @throws {DOMException} NotAllowedError (permission refused), NotFoundError (no camera)…
 */
export async function startCameraScan(video, onCode) {
  const reader = await createReader();
  let done = false;
  const controls = await reader.decodeFromConstraints(
    { video: { facingMode: { ideal: 'environment' } }, audio: false },
    video,
    (result, _error, ctrl) => {
      if (done || !result) return;
      const code = cleanCode(result.getText());
      if (!code) return;
      done = true;
      ctrl.stop();
      onCode(code);
    },
  );
  return controls;
}

/**
 * Message for a camera error.
 * @param {any} err
 */
export function cameraErrorMessage(err) {
  if (err?.name === 'NotAllowedError' || err?.name === 'SecurityError') {
    return 'L’accès à la caméra a été refusé. Autorisez-le dans les réglages du navigateur, ou importez une photo du code-barre.';
  }
  if (err?.name === 'NotFoundError' || err?.name === 'OverconstrainedError') {
    return 'Aucune caméra n’a été trouvée sur cet appareil. Importez une photo du code-barre ou saisissez les chiffres.';
  }
  return 'La caméra n’a pas pu démarrer. Importez une photo du code-barre ou saisissez les chiffres.';
}
