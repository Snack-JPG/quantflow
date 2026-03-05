import type { Metadata } from 'next'
import './globals.css'

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
      <body className="min-h-screen bg-background">{children}</body>
    </html>
  )
}