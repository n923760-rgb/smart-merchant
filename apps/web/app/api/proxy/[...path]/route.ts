import { NextRequest, NextResponse } from 'next/server';
const backend = process.env.BACKEND_URL ?? 'http://localhost:8000';
const secure = process.env.NODE_ENV === 'production';
async function forward(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  if (path.some(segment => segment === '..' || segment.includes('/'))) return NextResponse.json({ message: 'Invalid path' }, { status: 400 });
  const url = `${backend}/api/v1/${path.map(encodeURIComponent).join('/')}${req.nextUrl.search}`;
  let access = req.cookies.get('sm_access')?.value;
  let rotated: { access_token: string; refresh_token: string } | null = null;
  const body = ['GET', 'HEAD'].includes(req.method) ? undefined : await req.text();
  const call = (token: string | undefined) => fetch(url, { method: req.method, headers: { Authorization: `Bearer ${token ?? ''}`, 'X-Organization-ID': req.cookies.get('sm_org')?.value ?? '', 'Content-Type': 'application/json' }, body, cache: 'no-store' });
  let response = await call(access);
  if (response.status === 401 && req.cookies.get('sm_refresh')?.value) {
    const refreshed = await fetch(`${backend}/api/v1/auth/refresh`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: req.cookies.get('sm_refresh')?.value }), cache: 'no-store' });
    if (refreshed.ok) { rotated = await refreshed.json(); access = rotated!.access_token; response = await call(access); }
  }
  const result = new NextResponse(response.status === 204 ? null : await response.text(), { status: response.status, headers: { 'Content-Type': response.headers.get('Content-Type') ?? 'application/json' } });
  if (rotated) { result.cookies.set('sm_access', rotated.access_token, { httpOnly: true, secure, sameSite: 'strict', path: '/' }); result.cookies.set('sm_refresh', rotated.refresh_token, { httpOnly: true, secure, sameSite: 'strict', path: '/' }); }
  return result;
}
export const GET = forward; export const POST = forward; export const PATCH = forward; export const DELETE = forward;
