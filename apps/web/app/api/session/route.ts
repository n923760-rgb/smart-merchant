import { NextRequest, NextResponse } from 'next/server';
import { BffError, object, withBffLimits } from '../../../lib/bff';
const backend = process.env.BACKEND_URL ?? 'http://localhost:8000';
const secure = process.env.NODE_ENV === 'production';
export async function POST(req: NextRequest) {
  return withBffLimits(async scope => {
    const body = await scope.request(req);
    scope.json(body, 'request');
    const response = await scope.upstream(`${backend}/api/v1/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
    const data = scope.json(response.text, 'upstream');
    if (!response.ok) return NextResponse.json(data, { status: response.status, headers: { 'Cache-Control': 'no-store' } });
    if (!object(data) || typeof data.access_token !== 'string' || !data.access_token || typeof data.refresh_token !== 'string' || !data.refresh_token) throw new BffError(502, 'BFF_INVALID_SESSION', 'Sign in unavailable');
    const result = NextResponse.json({ authenticated: true }, { headers: { 'Cache-Control': 'no-store' } });
    result.cookies.set('sm_access', data.access_token, { httpOnly: true, secure, sameSite: 'strict', path: '/' });
    result.cookies.set('sm_refresh', data.refresh_token, { httpOnly: true, secure, sameSite: 'strict', path: '/' });
    result.cookies.set('sm_context', crypto.randomUUID(), { secure, sameSite: 'strict', path: '/' });
    result.cookies.delete('sm_org');
    return result;
  });
}
export async function DELETE(req: NextRequest) {
  const context = req.cookies.get('sm_context')?.value;
  if (context && req.headers.get('X-Session-Context') !== context) return NextResponse.json({ message: 'Session changed. Reload this page.' }, { status: 409 });
  const refresh = req.cookies.get('sm_refresh')?.value;
  if (refresh) await withBffLimits(async scope => {
    await scope.request(req);
    const response = await scope.upstream(`${backend}/api/v1/auth/logout`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: refresh }) });
    return new NextResponse(null, { status: response.status === 204 ? 204 : 502 });
  });
  // Local cleanup is guaranteed even if bounded revocation fails or times out.
  const response = NextResponse.json({ authenticated: false }, { headers: { 'Cache-Control': 'no-store' } });
  response.cookies.delete('sm_access'); response.cookies.delete('sm_refresh'); response.cookies.delete('sm_org'); response.cookies.delete('sm_context');
  return response;
}
