'use client';

import { ThemeProvider } from '@/contexts/ThemeContext';
import { ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}
