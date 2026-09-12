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
  return result;
}
export async function DELETE(req: NextRequest) {
  const refresh = req.cookies.get('sm_refresh')?.value; const access = req.cookies.get('sm_access')?.value;
  if (refresh && access) await fetch(`${backend}/api/v1/auth/logout`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${access}` }, body: JSON.stringify({ refresh_token: refresh }) }).catch(() => undefined);
  const response = NextResponse.json({ authenticated: false });
  response.cookies.delete('sm_access'); response.cookies.delete('sm_refresh'); response.cookies.delete('sm_org');
  return response;
}
