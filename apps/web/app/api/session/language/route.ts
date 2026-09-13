import { NextRequest, NextResponse } from 'next/server';
export async function POST(req: NextRequest) {
  const { language } = await req.json();
  if (language !== 'ar' && language !== 'en') return NextResponse.json({ message: 'Invalid language' }, { status: 400 });
  const response = NextResponse.json({ language });
  response.cookies.set('sm_lang', language, { sameSite: 'strict', secure: process.env.NODE_ENV === 'production', path: '/' });
  return response;
}
