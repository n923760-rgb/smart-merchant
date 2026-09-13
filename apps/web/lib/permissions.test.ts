import { describe, expect, it } from 'vitest';
import { canAccess, canManage, AuthorizationContext } from './permissions';
describe('navigation grants', () => {
  const ctx: AuthorizationContext = { organization: { id: 'org', name: 'Demo' }, permissions: [], branch_permissions: { abha: ['branches.read'] } };
  it('shows only authorized branch navigation', () => { expect(canAccess(ctx, 'branches.read')).toBe(true); expect(canAccess(ctx, 'users.read')).toBe(false); });
  it('does not turn branch read access into global create access', () => { expect(canManage(ctx, 'branches.create')).toBe(false); });
});
