import { NextRequest, NextResponse } from 'next/server';
import { withBffLimits } from '../../../../lib/bff';
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
  return withBffLimits(async scope => {
    const body = ['GET', 'HEAD'].includes(req.method) ? undefined : await scope.request(req);
    const response = await scope.upstream(url, { method: req.method, headers: { Authorization: `Bearer ${req.cookies.get('sm_access')?.value ?? ''}`, 'X-Organization-ID': req.cookies.get('sm_org')?.value ?? '', 'Content-Type': 'application/json' }, body });
    return new NextResponse(response.status === 204 ? null : response.text, { status: response.status, headers: { 'Content-Type': response.headers.get('Content-Type') ?? 'application/json', 'Cache-Control': 'no-store' } });
  });
}
export const GET = forward; export const POST = forward; export const PATCH = forward; export const DELETE = forward;
