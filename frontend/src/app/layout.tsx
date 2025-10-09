import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import ErrorBoundary from '@/components/shared/ErrorBoundary';
import { ToastProvider } from '@/components/shared/Toast';
import { AuthProvider } from '@/components/providers/AuthProvider';
import { ThemeProvider } from '@/components/providers/ThemeProvider';
import InitialThemeScript from '@/components/providers/InitialThemeScript';
import { HighlightProvider } from '@/components/providers/HighlightProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Automation Platform',
  description: 'Dynamic Automation Orchestration Platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <InitialThemeScript />
        <AuthProvider>
          <ThemeProvider>
            <HighlightProvider>
              <ErrorBoundary>
                <ToastProvider>
                  {children}
                </ToastProvider>
              </ErrorBoundary>
            </HighlightProvider>
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
