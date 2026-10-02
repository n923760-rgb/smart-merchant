import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';
function request(context: string, path: string[]) {
  return [new NextRequest('http://localhost:3000/api/proxy/' + path.join('/'), { method: 'POST', body: '{}', headers: { cookie: 'sm_context=beta; sm_access=fixture-access; sm_refresh=fixture-refresh; sm_org=fixture-org', 'X-Session-Context': context } }), { params: Promise.resolve({ path }) }] as const;
}
describe('context-bound proxy', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('rejects an earlier account command without forwarding it', async () => {
    vi.stubGlobal('fetch', vi.fn());
    expect((await POST(...request('alpha', ['branches']))).status).toBe(409);
    expect(fetch).not.toHaveBeenCalled();
  });
  it('returns 401 without racing refresh or changing cookies', async () => {
    const upstream = vi.fn(async () => Response.json({}, { status: 401 }));
    vi.stubGlobal('fetch', upstream);
    const result = await POST(...request('beta', ['branches']));
    expect(result.status).toBe(401);
    expect(result.headers.has('set-cookie')).toBe(false);
    expect(upstream).toHaveBeenCalledOnce();
    const [url, init] = upstream.mock.calls[0] as unknown as [string, RequestInit];
    expect(url.endsWith('/api/v1/branches')).toBe(true);
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer fixture-access');
    expect(new Headers(init.headers).get('X-Organization-ID')).toBe('fixture-org');
  });
  it('does not allow generic forwarding to bypass session cookie coordination', async () => {
    vi.stubGlobal('fetch', vi.fn());
    for (const operation of ['login', 'refresh', 'logout']) expect((await POST(...request('beta', ['auth', operation]))).status).toBe(400);
    expect(fetch).not.toHaveBeenCalled();
  });
});
