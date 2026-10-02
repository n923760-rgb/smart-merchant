import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST as login, DELETE as logout } from './session/route';
import { POST as refresh } from './session/refresh/route';
import { POST as proxy } from './proxy/[...path]/route';
import { POST as organization } from './session/organization/route';
import { POST as language } from './session/language/route';
function req(path: string, body?: string, method = 'POST') {
  return new NextRequest('http://localhost:3000/api/' + path, { method, body, headers: { cookie: 'sm_context=alpha; sm_refresh=fixture-refresh; sm_access=fixture-access; sm_org=fixture-org', 'X-Session-Context': 'alpha' } });
}
describe('BFF route failure contracts', () => {
  afterEach(() => { vi.clearAllTimers(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.unstubAllEnvs(); });
  it('rejects oversized login/proxy requests before any upstream action', async () => {
    vi.stubEnv('BFF_REQUEST_MAX_BYTES', '1024'); vi.stubGlobal('fetch', vi.fn());
    const oversized = '{}'.repeat(600);
    expect((await login(req('session', oversized))).status).toBe(413);
    expect((await proxy(req('proxy/branches', oversized), { params: Promise.resolve({ path: ['branches'] }) })).status).toBe(413);
    expect(fetch).not.toHaveBeenCalled();
  });
  it('normalizes malformed/local null JSON and does not set configuration cookies', async () => {
    vi.stubGlobal('fetch', vi.fn());
    for (const handler of [organization, language]) {
      for (const body of ['{', 'null']) {
        const result = await handler(req('session/config', body));
        expect(result.status).toBe(400);
        expect(result.headers.has('Set-Cookie')).toBe(false);
      }
    }
    expect((await login(req('session', '{'))).status).toBe(400);
    expect(fetch).not.toHaveBeenCalled();
  });
  it('rejects malformed or incomplete auth responses without writing credentials', async () => {
    for (const handler of [login, refresh]) {
      for (const body of ['{', '{}', '{"access_token":"fixture-access"}']) {
        vi.stubGlobal('fetch', vi.fn(async () => new Response(body)));
        const result = await handler(req('session', '{}'));
        expect(result.status).toBe(502);
        expect(result.headers.has('Set-Cookie')).toBe(false);
      }
    }
  });
  it('preserves existing credentials on refresh timeout and makes one upstream attempt', async () => {
    vi.useFakeTimers(); vi.stubEnv('BFF_TIMEOUT_MS', '100');
    const upstream = vi.fn(() => new Promise<Response>(() => undefined)); vi.stubGlobal('fetch', upstream);
    const operation = refresh(req('session/refresh'));
    await vi.advanceTimersByTimeAsync(101);
    const result = await operation;
    expect(result.status).toBe(504);
    expect(result.headers.has('Set-Cookie')).toBe(false);
    expect(upstream).toHaveBeenCalledOnce();
  });
  it('clears local logout cookies within the deadline even when revocation stalls', async () => {
    vi.useFakeTimers(); vi.stubEnv('BFF_TIMEOUT_MS', '100');
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)));
    const operation = logout(req('session', undefined, 'DELETE'));
    await vi.advanceTimersByTimeAsync(101);
    const result = await operation;
    expect(await result.json()).toEqual({ authenticated: false });
    for (const name of ['sm_access', 'sm_refresh', 'sm_org', 'sm_context']) expect(result.cookies.get(name)?.value).toBe('');
    expect(fetch).toHaveBeenCalledOnce();
  });
  it('does not replay a timed-out mutation or leak an upstream error', async () => {
    vi.useFakeTimers(); vi.stubEnv('BFF_TIMEOUT_MS', '100');
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)));
    const operation = proxy(req('proxy/branches', '{}'), { params: Promise.resolve({ path: ['branches'] }) });
    await vi.advanceTimersByTimeAsync(101);
    expect((await operation).status).toBe(504);
    expect(fetch).toHaveBeenCalledOnce();
  });
});
