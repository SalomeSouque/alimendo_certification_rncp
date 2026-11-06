import { identifyFood, validateImage, MAX_IMAGE_SIZE } from './vision';
import { setToken } from './token';
import { mockFetch, jsonResponse } from '../test/mockFetch';

const file = (type, size = 1000, name = 'photo') => new File([new Uint8Array(size)], name, { type });

describe('vision.js (POST /ai/vision)', () => {
  it('validateImage: accepts JPEG, PNG and WebP up to 5 MB', () => {
    expect(validateImage(file('image/jpeg'))).toBeNull();
    expect(validateImage(file('image/png'))).toBeNull();
    expect(validateImage(file('image/webp', MAX_IMAGE_SIZE))).toBeNull();
  });

  it('validateImage: rejects other formats, files over 5 MB and no file', () => {
    expect(validateImage(file('image/gif'))).toMatch(/JPEG, PNG ou WebP/);
    expect(validateImage(file('application/pdf'))).toMatch(/Format non pris en charge/);
    expect(validateImage(file('image/jpeg', MAX_IMAGE_SIZE + 1))).toMatch(/5 Mo maximum/);
    expect(validateImage(undefined)).toMatch(/Choisissez une photo/);
  });

  it('identifyFood: multipart body with the "image" field, bearer token, no manual Content-Type', async () => {
    setToken('jwt');
    const fetchMock = mockFetch(jsonResponse(200, { statut: 'echec', message: 'x' }));
    const photo = file('image/jpeg', 10, 'pomme.jpg');

    await identifyFood(photo);

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/ai\/vision$/);
    expect(options.method).toBe('POST');
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get('image').name).toBe('pomme.jpg');
    expect(options.headers.Authorization).toBe('Bearer jwt');
    expect(options.headers['Content-Type']).toBeUndefined();
    expect(options.signal).toBeDefined();
  });

  it('identifyFood: client timeout becomes an ApiError with a clear message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(Object.assign(new Error('aborted'), { name: 'AbortError' })));
    await expect(identifyFood(file('image/png'))).rejects.toMatchObject({
      status: 0,
      message: 'La réponse a pris trop de temps. Réessayez dans un instant.',
    });
  });
});
