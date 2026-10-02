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
export async function sessionFetch(path: '/api/session' | '/api/session/organization', init: RequestInit): Promise<Response> {
  const login = path === '/api/session' && init.method === 'POST';
  const expected = login ? sessionContext() : boundSessionContext();
  return withSessionLock(async () => {
    if (!login) assertContext(expected);
    const headers = new Headers(init.headers);
    if (!login && expected) headers.set('X-Session-Context', expected);
    const response = await fetch(path, { ...init, headers, credentials: 'same-origin', cache: 'no-store' });
    if (response.ok) observedContext = sessionContext();
    return response;
  });
}
