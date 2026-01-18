import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import '@/styles/globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'PolyHedge - Real World Hedging with Prediction Markets',
    description: 'Proactively hedge your real-life risks using prediction market portfolios.',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en">
            <body className={`${inter.className} min-h-screen bg-gray-50 text-gray-900`}>
                {children}
            </body>
        </html>
    )
}
