import { NextResponse } from 'next/server';

export class BffError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}
type Limits = { timeout: number; requestBytes: number; responseBytes: number };
function setting(name: string, fallback: number, min: number, max: number): number {
  const raw = process.env[name];
  if (raw === undefined) return fallback;
  const value = Number(raw);
  if (!/^\d+$/.test(raw) || !Number.isSafeInteger(value) || value < min || value > max) {
    throw new BffError(503, 'BFF_CONFIGURATION_ERROR', 'Service temporarily unavailable');
  }
  return value;
}
function limits(): Limits {
  return {
    timeout: setting('BFF_TIMEOUT_MS', 10_000, 100, 60_000),
    requestBytes: setting('BFF_REQUEST_MAX_BYTES', 65_536, 1_024, 1_048_576),
    responseBytes: setting('BFF_RESPONSE_MAX_BYTES', 1_048_576, 1_024, 8_388_608),
  };
}
export function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
export class BffScope {
  readonly controller = new AbortController();
  private readonly expiresAt: number;
  constructor(private readonly limits: Limits) { this.expiresAt = Date.now() + limits.timeout; }
  private check() {
    if (!this.controller.signal.aborted && Date.now() >= this.expiresAt) {
      this.controller.abort(new BffError(504, 'BFF_TIMEOUT', 'Request timed out. Check the result before trying again.'));
    }
    this.controller.signal.throwIfAborted();
  }
  wait<T>(promise: Promise<T>): Promise<T> {
    try { this.check(); } catch (error) { void promise.catch(() => undefined); return Promise.reject(error); }
    const signal = this.controller.signal;
    return new Promise<T>((resolve, reject) => {
      const abort = () => reject(signal.reason);
      signal.addEventListener('abort', abort, { once: true });
      promise.then(value => { signal.removeEventListener('abort', abort); resolve(value); },
        error => { signal.removeEventListener('abort', abort); reject(error); });
    });
  }
  json(text: string, source: 'request' | 'upstream'): unknown {
    try { return JSON.parse(text); }
    catch { throw new BffError(source === 'request' ? 400 : 502, 'BFF_INVALID_JSON', source === 'request' ? 'Invalid request body' : 'Upstream response unavailable'); }
  }
  private async read(body: ReadableStream<Uint8Array> | null, headers: Headers, source: 'request' | 'upstream'): Promise<string> {
    this.check();
    const cap = source === 'request' ? this.limits.requestBytes : this.limits.responseBytes;
    const failure = () => new BffError(source === 'request' ? 413 : 502, 'BFF_BODY_TOO_LARGE', source === 'request' ? 'Request body is too large' : 'Upstream response unavailable');
    const length = headers.get('content-length');
    if (length !== null && (!/^\d+$/.test(length) || Number(length) > cap)) {
      void body?.cancel().catch(() => undefined);
      if (!/^\d+$/.test(length)) throw new BffError(source === 'request' ? 400 : 502, 'BFF_INVALID_LENGTH', 'Invalid body length');
      throw failure();
    }
    if (!body) return '';
    const reader = body.getReader();
    let buffer = new Uint8Array(Math.min(8192, cap));
    let size = 0, complete = false;
    try {
      while (true) {
        const { done, value } = await this.wait(reader.read());
        if (done) { complete = true; break; }
        const needed = size + value.byteLength;
        if (needed > cap) throw failure();
        if (needed > buffer.byteLength) {
          const expanded = new Uint8Array(Math.min(cap, Math.max(needed, buffer.byteLength * 2)));
          expanded.set(buffer.subarray(0, size)); buffer = expanded;
        }
        buffer.set(value, size); size = needed;
      }
      this.check();
      return new TextDecoder('utf-8', { fatal: true }).decode(buffer.subarray(0, size));
    } catch (error) {
      if (error instanceof BffError) throw error;
      throw new BffError(source === 'request' ? 400 : 502, 'BFF_BODY_UNAVAILABLE', source === 'request' ? 'Invalid request body' : 'Upstream response unavailable');
    } finally {
      if (!complete) void reader.cancel().catch(() => undefined);
      reader.releaseLock();
    }
  }
  request(req: Request): Promise<string> { return this.read(req.body, req.headers, 'request'); }
  async requestJSON(req: Request): Promise<unknown> { return this.json(await this.request(req), 'request'); }
  async upstream(url: string, init: RequestInit) {
    this.check();
    const response = await this.wait(fetch(url, { ...init, cache: 'no-store', redirect: 'error', signal: this.controller.signal }));
    const text = await this.read(response.body, response.headers, 'upstream');
    return { status: response.status, ok: response.ok, headers: response.headers, text };
  }
}
export async function withBffLimits(action: (scope: BffScope) => Promise<NextResponse>): Promise<NextResponse> {
  let scope: BffScope | undefined, timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const config = limits();
    scope = new BffScope(config);
    timer = setTimeout(() => scope!.controller.abort(new BffError(504, 'BFF_TIMEOUT', 'Request timed out. Check the result before trying again.')), config.timeout);
    return await scope.wait(Promise.resolve().then(() => action(scope!)));
  } catch (error) {
    const failure = error instanceof BffError ? error : new BffError(502, 'BFF_UPSTREAM_UNAVAILABLE', 'Service temporarily unavailable');
    return NextResponse.json({ code: failure.code, message: failure.message }, { status: failure.status, headers: { 'Cache-Control': 'no-store' } });
  } finally {
    clearTimeout(timer);
    scope?.controller.abort();
  }
}
