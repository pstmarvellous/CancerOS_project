import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'CancerOS · Research workspace',
  description: 'Research prototype foundation. Not validated for diagnosis or treatment decisions.',
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return <html lang="en"><body>
    <a className="skip-link" href="#main">Skip to main content</a>
    <header className="header"><Link className="brand" href="/">CancerOS <span>Research workspace</span></Link><Link className="phase" href="/mesh-preview">Private mesh preview</Link></header>
    <div className="safety-notice">Research prototype. Not validated for diagnosis or treatment decisions.</div>
    <main id="main" tabIndex={-1}>{children}</main>
    <footer>Scientific capabilities and source access require separate verification.</footer>
  </body></html>;
}
