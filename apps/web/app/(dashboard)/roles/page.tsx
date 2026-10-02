'use client';
import { useQuery } from '@tanstack/react-query';
import { api, Page, Role } from '@/lib/api';
export default function Roles() { const roles = useQuery({ queryKey: ['roles'], queryFn: () => api<Page<Role>>('roles') }); return <section><h1>قوالب الأدوار</h1>{roles.data?.items.map(r => <article key={r.id}>{r.code} · {r.name}</article>)}</section>; }
