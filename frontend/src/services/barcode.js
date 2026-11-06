// src/services/barcode.js
// Barcode reading in the browser (ZXing). Nothing is sent to a server:
// the image or the camera stream stays on the device, only the digits are
// used afterwards (GET /score/code-barre/{code}).
// The library is loaded on demand so it does not weigh on the other pages.

import { BARCODE_PATTERN } from './score';

/**
 * Reader limited to the formats printed on food packaging.
 * TRY_HARDER is deliberately NOT set: in @zxing/browser 0.2.1 it makes the
 * reader rotate frames without a barcode, which throws
 * "Could not create a Canvas element" and silently stops the camera scan.
 * @returns {Promise<{ reader: object, isRetryable: (error: any) => boolean }>}
 */
async function createReader() {
  const [{ BrowserMultiFormatOneDReader }, lib] = await Promise.all([
    import('@zxing/browser'),
    import('@zxing/library'),
  ]);
  const { BarcodeFormat, DecodeHintType, NotFoundException, ChecksumException, FormatException } = lib;
  const hints = new Map([
    [DecodeHintType.POSSIBLE_FORMATS, [BarcodeFormat.EAN_13, BarcodeFormat.EAN_8, BarcodeFormat.UPC_A, BarcodeFormat.UPC_E]],
  ]);
  // Errors after which ZXing keeps scanning; any other one ends its scan loop.
  const isRetryable = (error) =>
    error instanceof NotFoundException || error instanceof ChecksumException || error instanceof FormatException;
  return { reader: new BrowserMultiFormatOneDReader(hints), isRetryable };
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
  const { reader } = await createReader();
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

const NO_FRAMES_TIMEOUT_MS = 8000;

function stopStream(stream) {
  stream?.getTracks().forEach((track) => track.stop());
}

/** Opens the back camera, or any camera when the device has no back camera. */
async function openCamera() {
  try {
    return await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
  } catch (err) {
    if (err?.name !== 'OverconstrainedError') throw err;
    return navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  }
}

/** Plays the stream in the video element and waits for the first image. */
async function showStream(video, stream) {
  video.muted = true;
  video.playsInline = true;
  video.srcObject = stream;
  await video.play();
  if (video.readyState >= 2) return; // HAVE_CURRENT_DATA: an image is available
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      video.removeEventListener('loadeddata', onData);
      reject(Object.assign(new Error('The camera sends no image'), { name: 'NoFramesError' }));
    }, NO_FRAMES_TIMEOUT_MS);
    function onData() {
      clearTimeout(timer);
      resolve();
    }
    video.addEventListener('loadeddata', onData, { once: true });
  });
}

/**
 * Starts the camera, shows it in the video element and calls onCode once
 * with the first valid code. onError is called if the scan stops on an
 * unexpected error (ZXing then releases the camera on its own).
 * The stream is opened here rather than by ZXing so that every failure
 * gives a named error (ZXing rejects with `false` when the video does not play).
 * @param {HTMLVideoElement} video - preview element, already displayed
 * @param {(code: string) => void} onCode
 * @returns {Promise<{ stop: () => void }>} controls, to release the camera
 * @throws {DOMException|Error} NotAllowedError, NotFoundError, NotReadableError, NoFramesError…
 */
export async function startCameraScan(video, onCode, onError) {
  if (!video) throw Object.assign(new Error('No preview element'), { name: 'NoPreviewError' });
  const stream = await openCamera();
  try {
    await showStream(video, stream);
    const { reader, isRetryable } = await createReader();
    let done = false;
    const controls = await reader.decodeFromStream(stream, video, (result, error, ctrl) => {
      if (done) return;
      if (error && !isRetryable(error)) {
        done = true;
        stopStream(stream);
        onError?.(Object.assign(error, { name: error.name === 'Error' ? 'ScanError' : error.name }));
        return;
      }
      if (!result) return;
      const code = cleanCode(result.getText());
      if (!code) return;
      done = true;
      ctrl.stop();
      stopStream(stream);
      onCode(code);
    });
    return {
      stop: () => {
        done = true;
        controls.stop();
        stopStream(stream);
      },
    };
  } catch (err) {
    stopStream(stream);
    throw err;
  }
}

/**
 * Message for a camera error.
 * @param {any} err
 */
export function cameraErrorMessage(err) {
  const name = err?.name ?? 'Error';
  const fallback = ' Vous pouvez importer une photo du code-barre ou saisir les chiffres.';
  const messages = {
    NotAllowedError: 'L’accès à la caméra a été refusé, par le navigateur ou par le système (réglages de confidentialité).',
    SecurityError: 'L’accès à la caméra a été refusé, par le navigateur ou par le système (réglages de confidentialité).',
    NotFoundError: 'Aucune caméra n’a été trouvée sur cet appareil.',
    OverconstrainedError: 'Aucune caméra compatible n’a été trouvée sur cet appareil.',
    NotReadableError: 'La caméra est déjà utilisée par une autre application (visioconférence, OBS…) ou bloquée par le système.',
    AbortError: 'La caméra a été interrompue au démarrage.',
    NoFramesError: 'La caméra s’est ouverte mais n’envoie pas d’image.',
    ScanError: 'La lecture du code-barre s’est arrêtée.',
  };
  return `${messages[name] ?? 'La caméra n’a pas pu démarrer.'}${fallback} (code : ${name})`;
}