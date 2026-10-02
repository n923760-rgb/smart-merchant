'use client';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api, Me } from '@/lib/api';
import { sessionFetch, SessionError } from '@/lib/session';
import { AuthorizationContext, canAccess } from '@/lib/permissions';

const links = [ ['/overview', 'الرئيسية', 'Overview', 'organization.read'], ['/branches', 'الفروع', 'Branches', 'branches.read'], ['/users', 'المستخدمون', 'Users', 'users.read'], ['/roles', 'الأدوار', 'Roles', 'roles.read'], ['/devices', 'الأجهزة', 'Devices', 'terminals.read'] ];
export function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter(); const pathname = usePathname(); const [org, setOrg] = useState(''); const [orgError, setOrgError] = useState(false);
  const me = useQuery({ queryKey: ['me'], queryFn: () => api<Me>('auth/me'), retry: false });
  useEffect(() => { if (me.error instanceof SessionError && me.error.status === 401) router.replace('/login'); }, [me.error, router]);
  useEffect(() => { if (me.data?.organizations?.length && !org && !orgError) { const id = me.data.organizations[0]; sessionFetch('/api/session/organization', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) }).then(response => { if (!response.ok) throw new Error('Organization unavailable'); setOrg(id); }).catch(() => setOrgError(true)); } }, [me.data, org, orgError]);
  const permissions = useQuery({ queryKey: ['context', org], enabled: !!org, queryFn: () => api<AuthorizationContext>('auth/context') });
  if (me.isError || orgError || permissions.isError) return <main role="alert">تعذّر تحميل الحساب. <button onClick={() => window.location.reload()}>إعادة المحاولة</button></main>;
  if (!me.data || !org || !permissions.data) return <main className="loading">جارٍ تحميل الحساب...</main>;
  const english = typeof document !== 'undefined' && document.documentElement.lang === 'en';
  if (!links.some(([href, , , code]) => href === pathname && canAccess(permissions.data, code))) return <main role="alert">{english ? 'Access denied.' : 'لا تملك صلاحية الوصول لهذه الصفحة.'}</main>;
  async function logout() { try { const response = await sessionFetch('/api/session', { method: 'DELETE' }); if (!response.ok) throw new Error('Logout unavailable'); router.replace('/login'); } catch { setOrgError(true); } }
  async function toggleLanguage() { await fetch('/api/session/language', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ language: english ? 'ar' : 'en' }) }); window.location.reload(); }
  return <div className="shell"><aside><h2>{english ? 'Smart Merchant' : 'مساعد التاجر'}</h2><nav>{links.filter(([, , , scope]) => canAccess(permissions.data!, scope)).map(([href, ar, en]) => <Link className={pathname === href ? 'active' : ''} href={href} key={href}>{english ? en : ar}</Link>)}</nav></aside><div className="body"><header><span>{me.data.name} · {org.slice(0, 8)}</span><span><button onClick={toggleLanguage}>{english ? 'العربية' : 'English'}</button> <button onClick={logout}>{english ? 'Sign out' : 'خروج'}</button></span></header><main>{children}</main></div></div>;
}
