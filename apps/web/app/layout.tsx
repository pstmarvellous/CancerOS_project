import type { Metadata } from 'next';
import { AppShell } from '../components/app-shell';
import './globals.css';

export const metadata: Metadata = {
  title: 'CancerOS · Explore Cancer Evolution in 3D',
  description: 'Explore tumor geometry, hypothetical scenarios and clinical observations in a breast cancer research digital twin.',
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return <html lang="en"><body>
    <AppShell/>
    <main id="main" tabIndex={-1}>{children}</main>
    <footer>CancerOS · Breast cancer research prototype · Synthetic demonstrations are labeled throughout.</footer>
  </body></html>;
}
