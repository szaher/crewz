import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import ErrorBoundary from '@/components/shared/ErrorBoundary';
import { ToastProvider } from '@/components/shared/Toast';
import { AuthProvider } from '@/components/providers/AuthProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'CrewAI Platform',
  description: 'Dynamic CrewAI Orchestration Platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <ErrorBoundary>
            <ToastProvider>
              {children}
            </ToastProvider>
          </ErrorBoundary>
        </AuthProvider>
      </body>
    </html>
  );
}
