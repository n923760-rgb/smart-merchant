import { afterEach, describe, expect, it, vi } from 'vitest';
import { sessionFetch, sessionRequest } from './session';

describe('browser request deadline', () => {
  afterEach(() => { vi.clearAllTimers(); vi.useRealTimers(); vi.unstubAllGlobals(); });
  it('releases the session lock after a hung request without resending it', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('document', { cookie: '' });
    let queue = Promise.resolve();
    vi.stubGlobal('navigator', { locks: { request: (_name: string, action: () => Promise<unknown>) => {
      const next = queue.then(action); queue = next.then(() => undefined, () => undefined); return next;
    } } });
    const upstream = vi.fn()
      .mockImplementationOnce(() => new Promise<Response>(() => undefined))
      .mockResolvedValueOnce(Response.json({ authenticated: true }));
    vi.stubGlobal('fetch', upstream);
    const timedOut = sessionFetch('/api/session', { method: 'POST', body: '{}' }).catch(error => error);
    const next = sessionFetch('/api/session', { method: 'POST', body: '{}' });
    await vi.advanceTimersByTimeAsync(65_001);
    expect(await timedOut).toMatchObject({ status: 504 });
    expect((await next).ok).toBe(true);
    expect(upstream).toHaveBeenCalledTimes(2); // Two explicit actions; no implicit retry.
    expect(upstream.mock.calls[0][1].signal.aborted).toBe(true);
  });
  it('bounds a partial response body and cancels the read', async () => {
    vi.useFakeTimers();
    const cancel = vi.fn();
    vi.stubGlobal('fetch', vi.fn(async () => new Response(new ReadableStream({ start(c) { c.enqueue(new Uint8Array([123])); }, cancel }))));
    const outcome = sessionRequest('/api/session').catch(error => error);
    await vi.advanceTimersByTimeAsync(65_001);
    expect(await outcome).toMatchObject({ status: 504 });
    expect(cancel).toHaveBeenCalled();
    expect(fetch).toHaveBeenCalledOnce();
  });
  it('preserves a complete large JSON response through the bounded browser reader', async () => {
    const data = { note: 'قهوة'.repeat(5000) };
    vi.stubGlobal('fetch', vi.fn(async () => Response.json(data)));
    expect(await (await sessionRequest('/api/session')).json()).toEqual(data);
  });
  it('rejects oversized browser responses and already-cancelled requests', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(new Uint8Array(8_388_609))));
    await expect(sessionRequest('/api/session')).rejects.toMatchObject({ status: 502 });
    const controller = new AbortController(); controller.abort();
    await expect(sessionRequest('/api/session', { signal: controller.signal })).rejects.toMatchObject({ status: 499 });
    expect(fetch).toHaveBeenCalledOnce();
  });
});
