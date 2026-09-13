export type Page<T> = { items: T[]; page: number; page_size: number };
export type Branch = { id: string; name: string; code: string; city: string | null; status: string };
export type User = { id: string; name: string; email: string; status: string; membership_id: string };
export type Role = { id: string; code: string; name: string };
export type Terminal = { id: string; name: string; branch_id: string; activation_status: string; last_seen_at: string | null; app_version: string | null };
export type Me = { id: string; name: string; email: string; organizations: string[] };
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/proxy/${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).message ?? `HTTP ${response.status}`);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
