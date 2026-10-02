import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';
function request(context = 'alpha', refresh = 'fixture-refresh') {
  return new NextRequest('http://localhost:3000/api/session/refresh', { method: 'POST', headers: { cookie: `sm_context=alpha; sm_refresh=${refresh}`, 'X-Session-Context': context } });
}
describe('dedicated BFF refresh', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('sets only HttpOnly credentials and returns no tokens or new context', async () => {
    const upstream = vi.fn(async () => Response.json({ access_token: 'fixture-access-2', refresh_token: 'fixture-refresh-2' }));
    vi.stubGlobal('fetch', upstream);
    const result = await POST(request());
    expect(await result.json()).toEqual({ authenticated: true });
    expect(result.cookies.get('sm_access')?.httpOnly).toBe(true);
    expect(result.cookies.get('sm_refresh')?.httpOnly).toBe(true);
    expect(result.cookies.get('sm_context')).toBeUndefined();
    expect(upstream).toHaveBeenCalledOnce();
    const [, init] = upstream.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ refresh_token: 'fixture-refresh' });
  });
  it('rejects stale or unbound context before contacting the backend', async () => {
    vi.stubGlobal('fetch', vi.fn());
    for (const context of ['beta', '']) {
      const result = await POST(request(context));
      expect(result.status).toBe(409);
      expect(result.headers.has('set-cookie')).toBe(false);
    }
    expect(fetch).not.toHaveBeenCalled();
  });
  it('does not overwrite cookies after rejected rotation', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({}, { status: 401 })));
    const result = await POST(request());
    expect(result.status).toBe(401);
    expect(result.headers.has('set-cookie')).toBe(false);
  });
});
