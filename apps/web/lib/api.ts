import { assertContext, boundSessionContext, SessionError, sessionRequest, withSessionLock } from './session';
export type Page<T> = { items: T[]; page: number; page_size: number };
export type Branch = { id: string; name: string; code: string; city: string | null; status: string };
export type User = { id: string; name: string; email: string; status: string; membership_id: string };
export type Role = { id: string; code: string; name: string };
export type Terminal = { id: string; name: string; branch_id: string; activation_status: string; last_seen_at: string | null; app_version: string | null };
export type Me = { id: string; name: string; email: string; organizations: string[] };

async function failure(response: Response, context: string | null): Promise<never> {
  const data = await response.json().catch(() => ({}));
  assertContext(context);
  throw new SessionError(response.status, data.message ?? `HTTP ${response.status}`);
}
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const context = boundSessionContext();
  const headers = new Headers(init?.headers);
  headers.set('Content-Type', 'application/json');
  if (context) headers.set('X-Session-Context', context);
  const call = () => sessionRequest(`/api/proxy/${path}`, { ...init, headers, credentials: 'same-origin', cache: 'no-store' });
  let response = await call();
  assertContext(context);
  if (response.status === 401 && context) {
    // A 401 is a rejected authorization, never a timeout or unknown command result.
    // Only replay bodies that can be sent again without consuming a stream.
    if (init?.body && typeof init.body !== 'string') return failure(response, context);
    response = await withSessionLock(async () => {
      assertContext(context);
      // Another tab/request may already have renewed the HttpOnly cookies.
      const probe = await sessionRequest('/api/proxy/auth/me', { headers, credentials: 'same-origin', cache: 'no-store' });
      assertContext(context);
      if (probe.status === 401) {
        const renewed = await sessionRequest('/api/session/refresh', { method: 'POST', headers, credentials: 'same-origin', cache: 'no-store' });
        assertContext(context);
        if (!renewed.ok) return renewed;
      } else if (!probe.ok) {
        return probe;
      }
      return call(); // Exactly one retry, with the original context and current cookies.
    });
  }
  assertContext(context);
  if (!response.ok) return failure(response, context);
  if (response.status === 204) return undefined as T;
  const data = await response.json() as T;
  assertContext(context);
  return data;
}
