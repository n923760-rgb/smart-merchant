'use client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

function SessionQueries({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());
  useEffect(() => () => client.clear(), [client]);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  // The root layout survives navigation. Remount its query provider at each
  // login boundary so account data and late requests cannot cross sessions.
  return <SessionQueries key={pathname === '/login' ? 'login' : 'dashboard'}>{children}</SessionQueries>;
}
