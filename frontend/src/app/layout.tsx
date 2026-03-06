import type { Metadata } from 'next'
import './globals.css'
import { Navigation } from '@/components/Navigation'

export const metadata: Metadata = {
  title: 'QuantFlow - Order Book Intelligence',
  description: 'Real-time multi-exchange order book analytics',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-zinc-950">
        <Navigation />
        <main className="max-w-[1920px] mx-auto">
          {children}
        </main>
      </body>
    </html>
  )
}