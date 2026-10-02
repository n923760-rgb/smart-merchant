import { NextRequest, NextResponse } from 'next/server';
const backend = process.env.BACKEND_URL ?? 'http://localhost:8000';
async function forward(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  if (path.some(segment => segment === '..' || segment.includes('/'))) return NextResponse.json({ message: 'Invalid path' }, { status: 400 });
  // Cookie-changing auth operations must use the dedicated session endpoints.
  if (path[0] === 'auth' && ['login', 'refresh', 'logout'].includes(path[1])) return NextResponse.json({ message: 'Use the session endpoint' }, { status: 400 });
  const context = req.cookies.get('sm_context')?.value;
  if (!context) return NextResponse.json({ message: 'Sign in again' }, { status: 401 });
  if (req.headers.get('X-Session-Context') !== context) return NextResponse.json({ message: 'Session changed. Reload this page.' }, { status: 409 });
  const url = `${backend}/api/v1/${path.map(encodeURIComponent).join('/')}${req.nextUrl.search}`;
  const body = ['GET', 'HEAD'].includes(req.method) ? undefined : await req.text();
  const response = await fetch(url, { method: req.method, headers: { Authorization: `Bearer ${req.cookies.get('sm_access')?.value ?? ''}`, 'X-Organization-ID': req.cookies.get('sm_org')?.value ?? '', 'Content-Type': 'application/json' }, body, cache: 'no-store' });
  return new NextResponse(response.status === 204 ? null : await response.text(), { status: response.status, headers: { 'Content-Type': response.headers.get('Content-Type') ?? 'application/json', 'Cache-Control': 'no-store' } });
}
export const GET = forward; export const POST = forward; export const PATCH = forward; export const DELETE = forward;
