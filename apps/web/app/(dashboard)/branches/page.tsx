'use client';
import { FormEvent, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, Branch, Page } from '@/lib/api';
import { AuthorizationContext, canManage } from '@/lib/permissions';
export default function Branches() {
  const [page, setPage] = useState(1); const [error, setError] = useState(''); const qc = useQueryClient();
  const list = useQuery({ queryKey: ['branches', page], queryFn: () => api<Page<Branch>>(`branches?page=${page}`) });
  const authorization = useQuery({ queryKey: ['context'], queryFn: () => api<AuthorizationContext>('auth/context') });
  async function create(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = event.currentTarget; const values = Object.fromEntries(new FormData(form)); try { await api('branches', { method: 'POST', body: JSON.stringify(values) }); form.reset(); qc.invalidateQueries({ queryKey: ['branches'] }); } catch (e) { setError(String(e)); } }
  async function change(branch: Branch, status: string) { try { await api(`branches/${branch.id}`, { method: 'PATCH', body: JSON.stringify({ status }) }); qc.invalidateQueries({ queryKey: ['branches'] }); } catch (e) { setError(String(e)); } }
  return <section><h1>الفروع</h1>{error && <p role="alert">{error}</p>}{authorization.data && canManage(authorization.data, 'branches.create') && <form onSubmit={create} className="row"><input name="name" placeholder="اسم الفرع" required /><input name="code" placeholder="رمز مثل ABH01" required /><input name="city" placeholder="المدينة" /><button>إضافة فرع</button></form>}<table><thead><tr><th>الاسم</th><th>الرمز</th><th>المدينة</th><th>الحالة</th><th>إجراء</th></tr></thead><tbody>{list.data?.items.map(b => <tr key={b.id}><td>{b.name}</td><td>{b.code}</td><td>{b.city}</td><td>{b.status}</td><td>{authorization.data && canManage(authorization.data, 'branches.update') && <><button onClick={() => { const name = prompt('اسم الفرع', b.name); if (name) api(`branches/${b.id}`, { method: 'PATCH', body: JSON.stringify({ name }) }).then(() => qc.invalidateQueries({ queryKey: ['branches'] })).catch(e => setError(String(e))); }}>تعديل</button><button onClick={() => change(b, b.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE')}>تبديل الحالة</button></>}</td></tr>)}</tbody></table><button disabled={page === 1} onClick={() => setPage(page - 1)}>السابق</button><button disabled={(list.data?.items.length ?? 0) < 20} onClick={() => setPage(page + 1)}>التالي</button></section>;
}
