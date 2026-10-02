'use client';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
export default function Overview() { const org = useQuery({ queryKey: ['org'], queryFn: () => api<{ id: string; name: string }[]>('organizations') }); return <section><h1>نظرة عامة</h1><p>{org.data?.[0]?.name ?? 'جارٍ تحميل المنشأة...'}</p><p>إدارة الفروع والموظفين والأجهزة من القائمة.</p></section>; }
