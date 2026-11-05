import { api, ApiError, SESSION_EXPIRED_EVENT } from './api';
import { setToken, getToken } from './token';
import { mockFetch, jsonResponse } from '../test/mockFetch';

describe('api.js transport', () => {
  it('sends JSON with the bearer token when one is stored', async () => {
    setToken('abc');
    const fetchMock = mockFetch(jsonResponse(200, { ok: true }));

    await api.post('/ai/chat', { question: 'test' });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBe('Bearer abc');
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(options.body).toBe(JSON.stringify({ question: 'test' }));
  });

  it('lets the browser set Content-Type for FormData (multipart boundary)', async () => {
    const fetchMock = mockFetch(jsonResponse(200, {}));
    const form = new FormData();
    form.append('image', new Blob(['x'], { type: 'image/png' }), 'a.png');

    await api.post('/ai/vision', form);

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers['Content-Type']).toBeUndefined();
    expect(options.body).toBe(form);
  });

  it('on 401 with a token: clears it and fires the session-expired event', async () => {
    setToken('expired');
    mockFetch(jsonResponse(401, { detail: 'Jeton absent, invalide ou expiré.' }));
    const listener = vi.fn();
    window.addEventListener(SESSION_EXPIRED_EVENT, listener);

    await expect(api.get('/auth/me')).rejects.toMatchObject({ status: 401 });

    expect(getToken()).toBeNull();
    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener);
  });

  it('on 401 without a token (wrong password): no session-expired event', async () => {
    mockFetch(jsonResponse(401, { detail: 'Email ou mot de passe incorrect.' }));
    const listener = vi.fn();
    window.addEventListener(SESSION_EXPIRED_EVENT, listener);

    await expect(api.post('/auth/login', {})).rejects.toThrow('Email ou mot de passe incorrect.');

    expect(listener).not.toHaveBeenCalled();
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener);
  });

  it('turns a 422 validation array into a readable message', async () => {
    mockFetch(jsonResponse(422, { detail: [{ msg: 'champ requis' }, { msg: 'trop court' }] }));
    await expect(api.post('/auth/register', {})).rejects.toThrow('champ requis trop court');
  });

  it('on 5xx without JSON body: generic "service unavailable" message', async () => {
    mockFetch(jsonResponse(503));
    const err = await api.get('/health').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(503);
    expect(err.message).toMatch(/momentanément indisponible/);
  });

  it('on network failure: ApiError with status 0', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(api.get('/health')).rejects.toMatchObject({ status: 0 });
  });
});