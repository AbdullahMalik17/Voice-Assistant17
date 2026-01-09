'use client';

import { ThemeProvider } from '@/contexts/ThemeContext';
import { SessionProvider } from '@/components/auth/SessionProvider';
import { ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <ThemeProvider>{children}</ThemeProvider>
    </SessionProvider>
  );
}
