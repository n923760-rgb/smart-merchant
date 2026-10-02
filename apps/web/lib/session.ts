// Tokens remain HttpOnly. This UUID only binds requests to an account/organization context.
export class SessionError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
export function sessionContext(): string | null {
  return document.cookie.split('; ').find(cookie => cookie.startsWith('sm_context='))?.slice('sm_context='.length) ?? null;
}
let observedContext: string | null | undefined;
export function boundSessionContext(): string | null {
  if (observedContext === undefined) observedContext = sessionContext();
  assertContext(observedContext);
  return observedContext;
}
export function assertContext(expected: string | null) {
  if (sessionContext() !== expected) throw new SessionError(409, 'Session changed. Reload this page.');
}
export async function withSessionLock<T>(action: () => Promise<T>): Promise<T> {
  if (!navigator.locks) throw new SessionError(503, 'Use a supported browser over HTTPS to manage your session.');
  return navigator.locks.request('smart-merchant-session', action);
}

// Longer than the maximum server deadline (60s), including transport/body delivery.
export async function sessionRequest(url: string, init?: RequestInit): Promise<Response> {
  if (init?.signal?.aborted) throw new SessionError(499, 'Request cancelled.');
  const controller = new AbortController();
  const expiresAt = Date.now() + 65_000;
  const check = () => {
    if (!controller.signal.aborted && Date.now() >= expiresAt) controller.abort(new SessionError(504, 'Request timed out. Check the result before trying again.'));
    if (controller.signal.aborted) throw controller.signal.reason;
  };
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let cancel: () => void = () => undefined;
  const deadline = new Promise<never>((_, reject) => {
    const stop = (error: SessionError) => {
      controller.abort(error);
      void reader?.cancel().catch(() => undefined);
      reject(error);
    };
    cancel = () => stop(new SessionError(499, 'Request cancelled.'));
    init?.signal?.addEventListener('abort', cancel, { once: true });
    timer = setTimeout(() => stop(new SessionError(504, 'Request timed out. Check the result before trying again.')), 65_000);
  });
  const operation = async () => {
    const response = await fetch(url, { ...init, signal: controller.signal });
    if (controller.signal.aborted) {
      void response.body?.cancel().catch(() => undefined);
      throw controller.signal.reason;
    }
    let buffer = new Uint8Array(8192);
    let size = 0;
    reader = response.body?.getReader();
    try {
      while (reader) {
        const { done, value } = await reader.read();
        check();
        if (done) break;
        const needed = size + value.byteLength;
        if (needed > 8_388_608) throw new SessionError(502, 'Response unavailable.');
        if (needed > buffer.byteLength) {
          const expanded = new Uint8Array(Math.min(8_388_608, Math.max(needed, buffer.byteLength * 2)));
          expanded.set(buffer.subarray(0, size)); buffer = expanded;
        }
        buffer.set(value, size); size = needed;
      }
      check();
      return new Response(size ? buffer.subarray(0, size) : null, { status: response.status, statusText: response.statusText, headers: response.headers });
    } finally {
      void reader?.cancel().catch(() => undefined);
      reader?.releaseLock();
    }
  };
  try { return await Promise.race([operation(), deadline]); }
  finally {
    clearTimeout(timer);
    init?.signal?.removeEventListener('abort', cancel);
  }
}

export async function sessionFetch(path: '/api/session' | '/api/session/organization', init: RequestInit): Promise<Response> {
  const login = path === '/api/session' && init.method === 'POST';
  const expected = login ? sessionContext() : boundSessionContext();
  return withSessionLock(async () => {
    if (!login) assertContext(expected);
    const headers = new Headers(init.headers);
    if (!login && expected) headers.set('X-Session-Context', expected);
    const response = await sessionRequest(path, { ...init, headers, credentials: 'same-origin', cache: 'no-store' });
    if (response.ok) observedContext = sessionContext();
    return response;
  });
}
