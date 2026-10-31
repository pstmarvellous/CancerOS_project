import type { Metadata } from 'next';
import { AppShell } from '../components/app-shell';
import './globals.css';

export const metadata: Metadata = {
  title: 'CancerOS · Research workspace',
  description: 'Research prototype foundation. Not validated for diagnosis or treatment decisions.',
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return <html lang="en"><body>
    <AppShell/>
    <main id="main" tabIndex={-1}>{children}</main>
    <footer>Scientific capabilities and source access require separate verification.</footer>
  </body></html>;
}
