import { describe, expect, it } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';
const id = '11111111-1111-4111-8111-111111111111';
function request(context: string, selected?: string) {
  return new NextRequest('http://localhost:3000/api/session/organization', { method: 'POST', body: JSON.stringify({ id }), headers: { cookie: 'sm_context=alpha' + (selected ? '; sm_org=' + selected : ''), 'X-Session-Context': context } });
}
describe('organization context boundary', () => {
  it('invalidates old requests when organization changes, but preserves context for repeated selection', async () => {
    const changed = await POST(request('alpha'));
    expect(changed.cookies.get('sm_context')?.value).not.toBe('alpha');
    expect(changed.cookies.get('sm_org')?.httpOnly).toBe(true);
    const same = await POST(request('alpha', id));
    expect(same.cookies.get('sm_context')).toBeUndefined();
  });
  it('rejects an old account selection before writing cookies', async () => {
    const result = await POST(request('beta'));
    expect(result.status).toBe(409);
    expect(result.headers.has('set-cookie')).toBe(false);
  });
});
