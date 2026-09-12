import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';

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
