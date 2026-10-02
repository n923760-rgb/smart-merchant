import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { DELETE, POST } from './route';

describe('web login proxy', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('stores tokens in HttpOnly cookies and does not return them to browser JavaScript', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({ access_token: 'access', refresh_token: 'refresh' })));
    const request = new NextRequest('http://localhost:3000/api/session', { method: 'POST', body: JSON.stringify({ email: 'owner@example.com', password: 'correct' }) });
    const response = await POST(request);
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ authenticated: true });
    expect(response.headers.get('set-cookie')).toContain('HttpOnly');
  });

  it('does not create a session on denied credentials', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({ code: 'AUTHENTICATION_FAILED' }, { status: 401 })));
    const request = new NextRequest('http://localhost:3000/api/session', { method: 'POST', body: '{}' });
    const response = await POST(request);
    expect(response.status).toBe(401);
    expect(response.headers.has('set-cookie')).toBe(false);
  });
});

describe('web logout proxy', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('revokes a refresh-only session and clears all local session cookies', async () => {
    const upstream = vi.fn(async () => new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', upstream);
    const request = new NextRequest('http://localhost:3000/api/session', {
      method: 'DELETE', headers: { cookie: 'sm_refresh=refresh-fixture; sm_org=org-fixture' },
    });
    const response = await DELETE(request);
    expect(upstream).toHaveBeenCalledOnce();
    const [url, init] = upstream.mock.calls[0] as unknown as [string, RequestInit];
    expect(url.endsWith('/api/v1/auth/logout')).toBe(true);
    expect(JSON.parse(init.body as string)).toEqual({ refresh_token: 'refresh-fixture' });
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' });
    expect(await response.json()).toEqual({ authenticated: false });
    for (const name of ['sm_access', 'sm_refresh', 'sm_org']) {
      expect(response.cookies.get(name)?.value).toBe('');
    }
  });

  it('clears local cookies when the backend is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('disposable network failure'); }));
    const response = await DELETE(new NextRequest('http://localhost:3000/api/session', {
      method: 'DELETE', headers: { cookie: 'sm_refresh=refresh-fixture' },
    }));
    expect(response.status).toBe(200);
    expect(response.cookies.get('sm_refresh')?.value).toBe('');
  });
});
