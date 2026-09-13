'use client';
import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
export default function Login() {
  const router = useRouter(); const [error, setError] = useState('');
  const english = typeof document !== 'undefined' && document.documentElement.lang === 'en';
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); const response = await fetch('/api/session', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: data.get('email'), password: data.get('password') }) }); if (!response.ok) { setError(english ? 'Invalid credentials' : 'بيانات الدخول غير صحيحة'); return; } router.push('/overview'); router.refresh(); }
  async function toggleLanguage() { await fetch('/api/session/language', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ language: english ? 'ar' : 'en' }) }); window.location.reload(); }
  return <main className="login"><form onSubmit={submit}><h1>{english ? 'Smart Merchant Assistant' : 'مساعد التاجر الذكي'}</h1><p>{english ? 'Owner and staff sign in' : 'تسجيل دخول المالك والموظفين'}</p><label>{english ? 'Email' : 'البريد الإلكتروني'}<input name="email" type="email" required /></label><label>{english ? 'Password' : 'كلمة المرور'}<input name="password" type="password" required /></label>{error && <p role="alert">{error}</p>}<button>{english ? 'Sign in' : 'دخول'}</button><button type="button" onClick={toggleLanguage}>{english ? 'العربية' : 'English'}</button></form></main>;
}
