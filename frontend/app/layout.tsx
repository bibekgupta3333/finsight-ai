import { Navigation } from '@/components/navigation';
import { ThemeProvider } from '@/components/providers/theme-provider';
import { ReactQueryProvider } from '@/lib/react-query-provider';
import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import { Toaster } from 'react-hot-toast';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: {
    default: 'FinSight AI - Advanced Fraud Detection System',
    template: '%s | FinSight AI',
  },
  description: 'AI-powered multi-agent fraud detection with advanced reasoning patterns including ReAct, Chain-of-Thought, and Tree-of-Thought. Real-time transaction analysis with unprecedented accuracy.',
  keywords: [
    'fraud detection',
    'AI fraud detection',
    'financial fraud',
    'transaction monitoring',
    'multi-agent system',
    'machine learning',
    'risk analysis',
    'fintech',
    'cybersecurity',
  ],
  authors: [{ name: 'FinSight AI Team' }],
  creator: 'FinSight AI',
  publisher: 'FinSight AI',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://finsight-ai.com',
    title: 'FinSight AI - Advanced Fraud Detection System',
    description: 'AI-powered multi-agent fraud detection with advanced reasoning patterns. Real-time transaction analysis with unprecedented accuracy.',
    siteName: 'FinSight AI',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'FinSight AI Platform',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FinSight AI - Advanced Fraud Detection System',
    description: 'AI-powered multi-agent fraud detection with advanced reasoning patterns.',
    images: ['/twitter-image.png'],
    creator: '@finsightai',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  metadataBase: new URL('https://finsight-ai.com'),
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="manifest" href="/manifest.json" />
        <link rel="icon" href="/favicon.ico" />
        <meta name="theme-color" content="#2563eb" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          enableColorScheme
          storageKey="finsight-theme"
        >
          <a href="#main-content" className="skip-to-main">
            Skip to main content
          </a>
          <ReactQueryProvider>
            <Navigation />
            <main id="main-content">
              {children}
            </main>
            <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#333',
                color: '#fff',
              },
              success: {
                duration: 3000,
                iconTheme: {
                  primary: '#22c55e',
                  secondary: '#fff',
                },
              },
              error: {
                duration: 5000,
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#fff',
                },
              },
            }}
          />
        </ReactQueryProvider>
      </ThemeProvider>
      </body>
    </html>
  );
}
