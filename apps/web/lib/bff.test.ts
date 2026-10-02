import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextResponse } from 'next/server';
import { withBffLimits } from './bff';
const url = 'http://fixture.invalid/api';
function request(body: BodyInit, headers?: HeadersInit) {
  return new Request(url, { method: 'POST', body, headers, duplex: 'half' } as RequestInit);
}
describe('BFF transport bounds', () => {
  afterEach(() => { vi.clearAllTimers(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

  it('accepts the exact UTF-8 byte boundary and rejects one extra byte', async () => {
    vi.stubEnv('BFF_REQUEST_MAX_BYTES', '1024');
    const exact = 'ا'.repeat(512);
    const ok = await withBffLimits(async scope => new NextResponse(await scope.request(request(exact))));
    expect(ok.status).toBe(200);
    expect(await ok.text()).toBe(exact);
    const denied = await withBffLimits(async scope => new NextResponse(await scope.request(request(exact + 'a'))));
    expect(denied.status).toBe(413);
  });

  it('counts chunked bytes despite a missing or understated Content-Length and cancels overflow', async () => {
    vi.stubEnv('BFF_REQUEST_MAX_BYTES', '1024');
    for (const headers of [undefined, { 'Content-Length': '1' }]) {
      const cancel = vi.fn();
      const body = new ReadableStream<Uint8Array>({ start(c) { c.enqueue(new Uint8Array(800)); c.enqueue(new Uint8Array(800)); }, cancel });
      const result = await withBffLimits(async scope => new NextResponse(await scope.request(request(body, headers))));
      expect(result.status).toBe(413);
      expect(cancel).toHaveBeenCalledOnce();
    }
  });

  it('rejects an announced oversized body before buffering it', async () => {
    vi.stubEnv('BFF_REQUEST_MAX_BYTES', '1024');
    const cancel = vi.fn();
    const body = new ReadableStream<Uint8Array>({ cancel });
    const result = await withBffLimits(async scope => new NextResponse(await scope.request(request(body, { 'Content-Length': '99999' }))));
    expect(result.status).toBe(413);
    expect(cancel).toHaveBeenCalledOnce();
  });

  it('handles split UTF-8 characters and rejects invalid UTF-8 without echoing the input', async () => {
    const split = new ReadableStream<Uint8Array>({ start(c) { c.enqueue(new Uint8Array([0xd8])); c.enqueue(new Uint8Array([0xa7])); c.close(); } });
    const ok = await withBffLimits(async scope => new NextResponse(await scope.request(request(split))));
    expect(await ok.text()).toBe('ا');
    const denied = await withBffLimits(async scope => new NextResponse(await scope.request(request(new Uint8Array([0xff])))));
    expect(denied.status).toBe(400);
  });

  it('preserves a large Unicode JSON body across many chunks and buffer growth', async () => {
    const text = JSON.stringify({ note: 'قهوة'.repeat(5000) });
    const bytes = new TextEncoder().encode(text);
    const body = new ReadableStream<Uint8Array>({ start(c) {
      for (let offset = 0; offset < bytes.byteLength; offset += 997) c.enqueue(bytes.subarray(offset, offset + 997));
      c.close();
    } });
    const result = await withBffLimits(async scope => new NextResponse(await scope.request(request(body))));
    expect(await result.text()).toBe(text);
  });

  it('times out an incomplete upload without reaching the backend', async () => {
    vi.useFakeTimers(); vi.stubEnv('BFF_TIMEOUT_MS', '100');
    const cancel = vi.fn();
    vi.stubGlobal('fetch', vi.fn());
    const body = new ReadableStream<Uint8Array>({ start(c) { c.enqueue(new TextEncoder().encode('{')); }, cancel });
    const operation = withBffLimits(async scope => {
      await scope.request(request(body));
      await scope.upstream(url, {});
      return NextResponse.json({});
    });
    await vi.advanceTimersByTimeAsync(101);
    expect((await operation).status).toBe(504);
    expect(cancel).toHaveBeenCalledOnce();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('expires while draining buffered empty chunks before the timer callback runs', async () => {
    vi.useFakeTimers(); vi.stubEnv('BFF_TIMEOUT_MS', '100');
    const body = new ReadableStream<Uint8Array>({ pull(c) {
      vi.setSystemTime(Date.now() + 30); c.enqueue(new Uint8Array(0));
    } });
    const result = await withBffLimits(async scope => new NextResponse(await scope.request(request(body))));
    expect(result.status).toBe(504);
  });

  it('uses one deadline across upload and upstream wait, with only one backend attempt', async () => {
    vi.useFakeTimers(); vi.stubEnv('BFF_TIMEOUT_MS', '100');
    const body = new ReadableStream<Uint8Array>({ start(c) { setTimeout(() => { c.enqueue(new TextEncoder().encode('{}')); c.close(); }, 60); } });
    const upstream = vi.fn(() => new Promise<Response>(resolve => { setTimeout(() => resolve(Response.json({})), 70); }));
    vi.stubGlobal('fetch', upstream);
    const operation = withBffLimits(async scope => {
      const content = await scope.request(request(body));
      await scope.upstream(url, { method: 'POST', body: content });
      return NextResponse.json({});
    });
    await vi.advanceTimersByTimeAsync(101);
    expect((await operation).status).toBe(504);
    expect(upstream).toHaveBeenCalledOnce();
    const [, init] = upstream.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.signal?.aborted).toBe(true);
  });

  it('bounds a stalled upstream body after headers and cancels the reader', async () => {
    vi.useFakeTimers(); vi.stubEnv('BFF_TIMEOUT_MS', '100');
    const cancel = vi.fn();
    vi.stubGlobal('fetch', vi.fn(async () => new Response(new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode('{')); }, cancel }))));
    const operation = withBffLimits(async scope => {
      const response = await scope.upstream(url, {});
      return new NextResponse(response.text);
    });
    await vi.advanceTimersByTimeAsync(101);
    expect((await operation).status).toBe(504);
    expect(cancel).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledOnce();
  });

  it('limits actual upstream bytes and sanitizes connection failures', async () => {
    vi.stubEnv('BFF_RESPONSE_MAX_BYTES', '1024');
    vi.stubGlobal('fetch', vi.fn(async () => new Response('x'.repeat(1025), { headers: { 'Content-Length': '1' } })));
    const large = await withBffLimits(async scope => new NextResponse((await scope.upstream(url, {})).text));
    expect(large.status).toBe(502);
    expect(large.headers.get('Cache-Control')).toBe('no-store');
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('fixture-only-sensitive-detail'); }));
    const failed = await withBffLimits(async scope => new NextResponse((await scope.upstream(url, {})).text));
    expect(failed.status).toBe(502);
    expect(await failed.text()).not.toContain('fixture-only-sensitive-detail');
  });

  it.each(['0', '-1', 'NaN', '1.5', '60001', '', '100ms'])('fails closed on invalid deadline %s', async value => {
    vi.stubEnv('BFF_TIMEOUT_MS', value); vi.stubGlobal('fetch', vi.fn());
    const result = await withBffLimits(async scope => new NextResponse((await scope.upstream(url, {})).text));
    expect(result.status).toBe(503);
    expect(fetch).not.toHaveBeenCalled();
  });
});
