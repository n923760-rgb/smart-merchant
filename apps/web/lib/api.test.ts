import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from './api';
import { sessionFetch } from './session';

function fixture() {
  const documentFixture = { cookie: 'sm_context=alpha' };
  let queue = Promise.resolve();
  const locks = { request: vi.fn((_name: string, action: () => Promise<unknown>) => {
    const next = queue.then(action);
    queue = next.then(() => undefined, () => undefined);
    return next;
  }) };
  vi.stubGlobal('document', documentFixture);
  vi.stubGlobal('navigator', { locks });
  return documentFixture;
}
describe('session renewal coordinator', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('coalesces concurrent 401 responses and a late 401 without sharing tokens with JavaScript', async () => {
    fixture();
    let renewed = false; let refreshes = 0; let businessCalls = 0;
    let releaseLate!: () => void;
    const late = new Promise<void>(resolve => { releaseLate = resolve; });
    const upstream = vi.fn(async (url: string, init?: RequestInit) => {
      expect(new Headers(init?.headers).get('X-Session-Context')).toBe('alpha');
      if (url === '/api/session/refresh') { refreshes++; renewed = true; return Response.json({ authenticated: true }); }
      if (url === '/api/proxy/auth/me') return Response.json({}, { status: renewed ? 200 : 401 });
      businessCalls++;
      if (url.endsWith('/late') && !renewed) { await late; return Response.json({}, { status: 401 }); }
      return Response.json({ ok: true }, { status: renewed ? 200 : 401 });
    });
    vi.stubGlobal('fetch', upstream);
    const delayed = api('late');
    const responses = await Promise.all([api('branches'), api('users')]);
    releaseLate();
    expect(await delayed).toEqual({ ok: true });
    expect(responses).toEqual([{ ok: true }, { ok: true }]);
    expect(refreshes).toBe(1);
    expect(businessCalls).toBe(6);
    expect(upstream.mock.calls.every(([, init]) => !new Headers(init?.headers).has('Authorization'))).toBe(true);
  });

  it('rejects an earlier account response before refresh or retry under the next account', async () => {
    const doc = fixture();
    vi.stubGlobal('fetch', vi.fn(async () => {
      doc.cookie = 'sm_context=beta';
      return Response.json({}, { status: 401 });
    }));
    await expect(api('branches', { method: 'POST', body: '{}' })).rejects.toMatchObject({ status: 409 });
    expect(fetch).toHaveBeenCalledOnce();
  });

  it('blocks a queued organization change after another account has logged in', async () => {
    const doc = fixture();
    const operation = sessionFetch('/api/session/organization', { method: 'POST', body: '{}' });
    doc.cookie = 'sm_context=beta';
    vi.stubGlobal('fetch', vi.fn());
    await expect(operation).rejects.toMatchObject({ status: 409 });
    expect(fetch).not.toHaveBeenCalled();
  });

  it('does not retry a business command after rejected refresh or an unknown upstream result', async () => {
    fixture();
    const upstream = vi.fn(async (url: string) => Response.json({}, { status: url === '/api/proxy/timeout' ? 504 : 401 }));
    vi.stubGlobal('fetch', upstream);
    await expect(api('branches', { method: 'POST', body: '{}' })).rejects.toMatchObject({ status: 401 });
    expect(upstream.mock.calls.map(([url]) => url)).toEqual(['/api/proxy/branches', '/api/proxy/auth/me', '/api/session/refresh']);
    upstream.mockClear();
    await expect(api('timeout', { method: 'POST', body: '{}' })).rejects.toMatchObject({ status: 504 });
    expect(upstream).toHaveBeenCalledOnce();
  });

  it('never rotates without cross-tab coordination support', async () => {
    fixture(); vi.stubGlobal('navigator', {});
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({}, { status: 401 })));
    await expect(api('branches')).rejects.toMatchObject({ status: 503 });
    expect(fetch).toHaveBeenCalledOnce();
  });

  it('does not replay a consumed request body', async () => {
    fixture();
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({}, { status: 401 })));
    await expect(api('branches', { method: 'POST', body: new FormData() })).rejects.toMatchObject({ status: 401 });
    expect(fetch).toHaveBeenCalledOnce();
  });
});
