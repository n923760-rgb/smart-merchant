import './style.css';
import { Providers } from '@/components/providers';
import { cookies } from 'next/headers';
export default async function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  const language = (await cookies()).get('sm_lang')?.value === 'en' ? 'en' : 'ar';
  return <html lang={language} dir={language === 'ar' ? 'rtl' : 'ltr'}><body><Providers>{children}</Providers></body></html>;
}
