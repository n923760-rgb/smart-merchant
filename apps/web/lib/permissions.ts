export type AuthorizationContext = { organization: { id: string; name: string }; permissions: string[]; branch_permissions: Record<string, string[]> };
export function canAccess(context: AuthorizationContext, code: string): boolean {
  return context.permissions.includes(code) || Object.values(context.branch_permissions).some(codes => codes.includes(code));
}
export function canManage(context: AuthorizationContext, code: string): boolean {
  return context.permissions.includes(code);
}
