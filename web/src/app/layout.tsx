import type { Metadata } from 'next';
import { Inter, Orbitron } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const orbitron = Orbitron({ subsets: ['latin'], variable: '--font-orbitron' });

export const metadata: Metadata = {
  title: 'NEXUS AI - Voice Assistant',
  description: 'Next-generation AI voice assistant with advanced agentic capabilities',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${orbitron.variable} ${inter.className}`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
