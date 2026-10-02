import { NextRequest, NextResponse } from 'next/server';
import { object, withBffLimits } from '../../../../lib/bff';
export async function POST(req: NextRequest) {
  const context = req.cookies.get('sm_context')?.value;
  if (!context) return NextResponse.json({ message: 'Sign in again' }, { status: 401 });
  if (req.headers.get('X-Session-Context') !== context) return NextResponse.json({ message: 'Session changed. Reload this page.' }, { status: 409 });
  return withBffLimits(async scope => {
    const data = await scope.requestJSON(req);
    const id = object(data) ? data.id : undefined;
    if (typeof id !== 'string' || !/^[0-9a-f-]{36}$/i.test(id)) return NextResponse.json({ message: 'Invalid organization' }, { status: 400 });
    const result = NextResponse.json({ id }, { headers: { 'Cache-Control': 'no-store' } });
    const options = { secure: process.env.NODE_ENV === 'production', sameSite: 'strict' as const, path: '/' };
    result.cookies.set('sm_org', id, { ...options, httpOnly: true });
    if (req.cookies.get('sm_org')?.value !== id) result.cookies.set('sm_context', crypto.randomUUID(), options);
    return result;
  });
}
