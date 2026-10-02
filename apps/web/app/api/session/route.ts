import { NextRequest, NextResponse } from 'next/server';
const backend = process.env.BACKEND_URL ?? 'http://localhost:8000';
const secure = process.env.NODE_ENV === 'production';
export async function POST(req: NextRequest) {
  const response = await fetch(`${backend}/api/v1/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: await req.text(), cache: 'no-store' });
  const data = await response.json();
  if (!response.ok) return NextResponse.json(data, { status: response.status });
  const result = NextResponse.json({ authenticated: true });
  result.cookies.set('sm_access', data.access_token, { httpOnly: true, secure, sameSite: 'strict', path: '/' });
  result.cookies.set('sm_refresh', data.refresh_token, { httpOnly: true, secure, sameSite: 'strict', path: '/' });
  result.cookies.set('sm_context', crypto.randomUUID(), { secure, sameSite: 'strict', path: '/' });
  result.cookies.delete('sm_org');
  result.headers.set('Cache-Control', 'no-store');
  return result;
}
export async function DELETE(req: NextRequest) {
  const context = req.cookies.get('sm_context')?.value;
  if (context && req.headers.get('X-Session-Context') !== context) return NextResponse.json({ message: 'Session changed. Reload this page.' }, { status: 409 });
  const refresh = req.cookies.get('sm_refresh')?.value;
  if (refresh) await fetch(`${backend}/api/v1/auth/logout`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: refresh }), cache: 'no-store' }).catch(() => undefined);
  const response = NextResponse.json({ authenticated: false });
  response.cookies.delete('sm_access'); response.cookies.delete('sm_refresh'); response.cookies.delete('sm_org'); response.cookies.delete('sm_context');
  response.headers.set('Cache-Control', 'no-store');
  return response;
}
