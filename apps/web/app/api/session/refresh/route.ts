import { NextRequest, NextResponse } from 'next/server';
import { BffError, object, withBffLimits } from '../../../../lib/bff';
const backend = process.env.BACKEND_URL ?? 'http://localhost:8000';
const secure = process.env.NODE_ENV === 'production';
export async function POST(req: NextRequest) {
  const context = req.cookies.get('sm_context')?.value;
  if (!context) return NextResponse.json({ message: 'Sign in again' }, { status: 401 });
  if (req.headers.get('X-Session-Context') !== context) return NextResponse.json({ message: 'Session changed. Reload this page.' }, { status: 409 });
  const refresh = req.cookies.get('sm_refresh')?.value;
  if (!refresh) return NextResponse.json({ message: 'Sign in again' }, { status: 401 });
  return withBffLimits(async scope => {
    await scope.request(req);
    const response = await scope.upstream(`${backend}/api/v1/auth/refresh`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: refresh }) });
    if (!response.ok) return NextResponse.json({ message: response.status === 401 ? 'Sign in again' : 'Session renewal unavailable' }, { status: response.status, headers: { 'Cache-Control': 'no-store' } });
    const data = scope.json(response.text, 'upstream');
    if (!object(data) || typeof data.access_token !== 'string' || !data.access_token || typeof data.refresh_token !== 'string' || !data.refresh_token) throw new BffError(502, 'BFF_INVALID_SESSION', 'Session renewal unavailable');
    const result = NextResponse.json({ authenticated: true }, { headers: { 'Cache-Control': 'no-store' } });
    result.cookies.set('sm_access', data.access_token, { httpOnly: true, secure, sameSite: 'strict', path: '/' });
    result.cookies.set('sm_refresh', data.refresh_token, { httpOnly: true, secure, sameSite: 'strict', path: '/' });
    return result;
  });
}
