import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/components/providers/AuthProvider";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { Toaster } from "@/components/ui/sonner";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: {
    template: "%s - specfinder.io",
    default: "Any project detail - instantly available | specfinder.io",
  },
  description: "Ask questions about your construction PDFs and get instant answers, instead of digging through messy, hard-to-search documents. AI-powered construction document processing and Q&A system.",
  keywords: ["construction", "PDF", "documents", "AI", "Q&A", "project management", "specifications"],
  authors: [{ name: "specfinder.io" }],
  creator: "specfinder.io",
  publisher: "specfinder.io",
  metadataBase: new URL('https://specfinder.io'),
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://specfinder.io',
    siteName: 'specfinder.io',
    title: 'Any project detail - instantly available',
    description: 'Ask questions about your construction PDFs and get instant answers, instead of digging through messy, hard-to-search documents.',
    images: [
      {
        url: '/video-poster.jpeg',
        width: 1200,
        height: 630,
        alt: 'specfinder.io - AI-powered construction document processing',
      }
    ],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@specfinder_io',
    creator: '@specfinder_io',
    title: 'Any project detail - instantly available',
    description: 'Ask questions about your construction PDFs and get instant answers, instead of digging through messy, hard-to-search documents.',
    images: ['/video-poster.jpeg'],
  },
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
    ],
    apple: '/apple-touch-icon.png',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} font-sans antialiased bg-background text-foreground`}
      >
        <QueryProvider>
          <AuthProvider>
            <div className="min-h-screen flex flex-col">
              {children}
            </div>
            <Toaster />
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
