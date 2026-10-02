import { NextRequest, NextResponse } from 'next/server';
import { object, withBffLimits } from '../../../../lib/bff';
export async function POST(req: NextRequest) {
  return withBffLimits(async scope => {
    const data = await scope.requestJSON(req);
    const language = object(data) ? data.language : undefined;
    if (language !== 'ar' && language !== 'en') return NextResponse.json({ message: 'Invalid language' }, { status: 400 });
    const response = NextResponse.json({ language }, { headers: { 'Cache-Control': 'no-store' } });
    response.cookies.set('sm_lang', language, { sameSite: 'strict', secure: process.env.NODE_ENV === 'production', path: '/' });
    return response;
  });
}
