import { NextRequest, NextResponse } from 'next/server';
export async function POST(req: NextRequest) {
  const { id } = await req.json();
  if (typeof id !== 'string' || !/^[0-9a-f-]{36}$/i.test(id)) return NextResponse.json({ message: 'Invalid organization' }, { status: 400 });
  const result = NextResponse.json({ id });
  result.cookies.set('sm_org', id, { httpOnly: true, secure: process.env.NODE_ENV === 'production', sameSite: 'strict', path: '/' });
  return result;
}
