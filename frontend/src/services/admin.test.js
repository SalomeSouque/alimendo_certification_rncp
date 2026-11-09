import { mockFetch, jsonResponse } from '../test/mockFetch';
import { isAdmin, listAccounts, setAiAccess } from './admin';

describe('admin service', () => {
  it('isAdmin: true only for the admin role', () => {
    expect(isAdmin({ role: 'admin' })).toBe(true);
    expect(isAdmin({ role: 'user' })).toBe(false);
    expect(isAdmin(null)).toBe(false);
  });

  it('listAccounts: GET /admin/utilisateurs with the JWT', async () => {
    localStorage.setItem('alimendo_token', 'admin-token');
    const fetchMock = mockFetch(jsonResponse(200, []));

    await expect(listAccounts()).resolves.toEqual([]);

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/admin\/utilisateurs$/);
    expect(options.method).toBe('GET');
    expect(options.headers.Authorization).toBe('Bearer admin-token');
  });

  it('setAiAccess: PATCH /admin/utilisateurs/{id}/acces-ia with { acces_ia }', async () => {
    const account = { id: 12, email: 'camille@exemple.fr', role: 'user', created_at: '2026-11-08T10:00:00Z', acces_ia: true };
    const fetchMock = mockFetch(jsonResponse(200, account));

    await expect(setAiAccess(12, true)).resolves.toEqual(account);

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/admin\/utilisateurs\/12\/acces-ia$/);
    expect(options.method).toBe('PATCH');
    expect(JSON.parse(options.body)).toEqual({ acces_ia: true });
  });

  it('setAiAccess: 404 becomes an ApiError with the backend message', async () => {
    mockFetch(jsonResponse(404, { detail: 'Compte introuvable.' }));
    await expect(setAiAccess(99, false)).rejects.toMatchObject({ status: 404, message: 'Compte introuvable.' });
  });
});
