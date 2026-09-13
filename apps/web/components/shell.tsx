'use client';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api, Me } from '@/lib/api';
import { AuthorizationContext, canAccess } from '@/lib/permissions';

const links = [ ['/overview', 'الرئيسية', 'Overview', 'organization.read'], ['/branches', 'الفروع', 'Branches', 'branches.read'], ['/users', 'المستخدمون', 'Users', 'users.read'], ['/roles', 'الأدوار', 'Roles', 'roles.read'], ['/devices', 'الأجهزة', 'Devices', 'terminals.read'] ];
export function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter(); const pathname = usePathname(); const [org, setOrg] = useState('');
  const me = useQuery({ queryKey: ['me'], queryFn: () => api<Me>('auth/me'), retry: false });
  useEffect(() => { if (me.isError) router.replace('/login'); }, [me.isError, router]);
  useEffect(() => { if (me.data?.organizations?.length && !org) { const id = me.data.organizations[0]; fetch('/api/session/organization', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) }).then(() => setOrg(id)); } }, [me.data, org]);
  const permissions = useQuery({ queryKey: ['context', org], enabled: !!org, queryFn: () => api<AuthorizationContext>('auth/context') });
  if (!me.data || !org || !permissions.data) return <main className="loading">جارٍ تحميل الحساب...</main>;
  const english = typeof document !== 'undefined' && document.documentElement.lang === 'en';
  if (!links.some(([href, , , code]) => href === pathname && canAccess(permissions.data, code))) return <main role="alert">{english ? 'Access denied.' : 'لا تملك صلاحية الوصول لهذه الصفحة.'}</main>;
  async function logout() { await fetch('/api/session', { method: 'DELETE' }); router.replace('/login'); }
  async function toggleLanguage() { await fetch('/api/session/language', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ language: english ? 'ar' : 'en' }) }); window.location.reload(); }
  return <div className="shell"><aside><h2>{english ? 'Smart Merchant' : 'مساعد التاجر'}</h2><nav>{links.filter(([, , , scope]) => canAccess(permissions.data!, scope)).map(([href, ar, en]) => <Link className={pathname === href ? 'active' : ''} href={href} key={href}>{english ? en : ar}</Link>)}</nav></aside><div className="body"><header><span>{me.data.name} · {org.slice(0, 8)}</span><span><button onClick={toggleLanguage}>{english ? 'العربية' : 'English'}</button> <button onClick={logout}>{english ? 'Sign out' : 'خروج'}</button></span></header><main>{children}</main></div></div>;
}
