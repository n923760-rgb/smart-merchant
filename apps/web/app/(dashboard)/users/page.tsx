'use client';
import { FormEvent, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, Page, Role, User, Branch } from '@/lib/api';
import { AuthorizationContext, canManage } from '@/lib/permissions';

type Detail = User & {
  membership_status: string;
  roles: { assignment_id: string; code: string; branch_id: string | null }[];
};

export default function Users() {
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const qc = useQueryClient();
  const users = useQuery({ queryKey: ['users'], queryFn: () => api<Page<User>>('users') });
  const roles = useQuery({ queryKey: ['roles'], queryFn: () => api<Page<Role>>('roles') });
  const branches = useQuery({ queryKey: ['branches'], queryFn: () => api<Page<Branch>>('branches') });
  const authorization = useQuery({ queryKey: ['context'], queryFn: () => api<AuthorizationContext>('auth/context') });
  const detail = useQuery({ queryKey: ['user', selected], enabled: !!selected, queryFn: () => api<Detail>(`users/${selected}`) });
  const mayInvite = authorization.data && canManage(authorization.data, 'users.invite');
  const mayGrant = authorization.data && canManage(authorization.data, 'roles.manage');

  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    try {
      await api('users', { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(e.currentTarget))) });
      qc.invalidateQueries({ queryKey: ['users'] }); e.currentTarget.reset();
    } catch (err) { setError(String(err)); }
  }

  async function assign(id: string, form: HTMLFormElement) {
    try {
      const data = new FormData(form);
      await api(`users/${id}/roles`, { method: 'POST', body: JSON.stringify({ role_id: data.get('role_id'), branch_id: data.get('branch_id') || null }) });
      qc.invalidateQueries({ queryKey: ['user', id] });
      setError('');
    } catch (err) { setError(String(err)); }
  }

  async function remove(id: string, assignment: string) {
    try {
      await api(`users/${id}/roles/${assignment}`, { method: 'DELETE' });
      qc.invalidateQueries({ queryKey: ['user', id] });
    } catch (err) { setError(String(err)); }
  }

  return <section>
    <h1>المستخدمون</h1>{error && <p role="alert">{error}</p>}
    {mayInvite && <form onSubmit={add} className="row">
      <input name="name" placeholder="الاسم" required />
      <input name="email" type="email" placeholder="البريد" required />
      <input name="password" type="password" minLength={12} placeholder="كلمة مرور مؤقتة" required />
      <button>إضافة</button>
    </form>}
    {users.data?.items.map(u => <article key={u.id}>
      <b>{u.name}</b> · {u.email} · {u.status} <button onClick={() => setSelected(selected === u.id ? null : u.id)}>عرض العضوية</button>
      {selected === u.id && detail.data && <div>
        <p>العضوية: {detail.data.membership_status}</p>
        {detail.data.roles.map(role => <p key={role.assignment_id}>
          {role.code} · {role.branch_id ? branches.data?.items.find(b => b.id === role.branch_id)?.name ?? role.branch_id : 'المنشأة كاملة'}
          {mayGrant && <button onClick={() => remove(u.id, role.assignment_id)}>إزالة الدور</button>}
        </p>)}
      </div>}
      {mayGrant && <form onSubmit={e => { e.preventDefault(); assign(u.id, e.currentTarget); }} className="row">
        <select name="role_id">{roles.data?.items.map(r => <option key={r.id} value={r.id}>{r.code}</option>)}</select>
        <select name="branch_id"><option value="">المنشأة كاملة</option>{branches.data?.items.map(b => <option value={b.id} key={b.id}>{b.name}</option>)}</select>
        <button>تعيين الدور</button>
      </form>}
      {authorization.data && canManage(authorization.data, 'users.manage') && <button onClick={() => api(`users/${u.id}/disable`, { method: 'POST' }).then(() => qc.invalidateQueries({ queryKey: ['users'] })).catch(e => setError(String(e)))}>تعطيل العضوية</button>}
    </article>)}
  </section>;
}
