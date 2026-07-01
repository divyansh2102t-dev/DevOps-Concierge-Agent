import './globals.css';
import { AppProvider } from './context/AppContext';

export const metadata = {
  title: 'DevOps Concierge Agent — Enterprise AI Automation',
  description: 'AI-powered DevOps automation platform. Scaffold projects, provision AWS infrastructure, deploy to Vercel, generate production Kubernetes manifests, and orchestrate local Kafka pipelines through natural conversation.',
  keywords: 'devops, ai agent, kubernetes, docker, aws, kafka, terraform, nextjs, vercel, github actions, automation',
  metadataBase: new URL('http://localhost:3000'),
  robots: {
    index: true,
    follow: true,
  },
  themeColor: '#090d16',
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
  },
  openGraph: {
    title: 'DevOps Concierge Agent — Enterprise AI Automation',
    description: 'Scaffold, deploy, and document production-ready projects through conversation.',
    type: 'website',
    locale: 'en_US',
    images: [
      {
        url: '/icon-512.png',
        width: 512,
        height: 512,
        alt: 'DevOps Concierge Agent Logo',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'DevOps Concierge Agent — Enterprise AI Automation',
    description: 'Scaffold, deploy, and document production-ready projects through conversation.',
    images: ['/icon-512.png'],
  },
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'DevOps Agent',
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
        {/* PWA Apple Touch Icon */}
        <link rel="apple-touch-icon" href="/icon-192.png" />
        {/* Inline Client-side Service Worker Registration */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js').then(function(reg) {
                    console.log('ServiceWorker registration successful with scope: ', reg.scope);
                  }, function(err) {
                    console.log('ServiceWorker registration failed: ', err);
                  });
                });
              }
            `,
          }}
        />
      </head>
      <body>
        <AppProvider>
          {children}
        </AppProvider>
      </body>
    </html>
  );
}
