import type { Metadata } from 'next';
import { Inter, JetBrains_Mono, Newsreader } from 'next/font/google';
import './globals.css';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-mono',
  subsets: ['latin'],
  display: 'swap',
});

const newsreader = Newsreader({
  variable: '--font-newsreader',
  subsets: ['latin'],
  display: 'swap',
  style: ['normal', 'italic'],
});

export const metadata: Metadata = {
  title: 'FRAUD CONSOLE · TigerGraph × HHGOA',
  description: 'Enterprise Fraud Review Console & Autonomous Agent Intelligence',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} ${newsreader.variable} dark`}
      style={{ colorScheme: 'dark' }}
    >
      <body className="bg-[#0A0E13] text-[#E8EEF4] antialiased min-h-screen flex flex-col selection:bg-[#F5A524] selection:text-[#0A0E13]">
        {children}
      </body>
    </html>
  );
}
