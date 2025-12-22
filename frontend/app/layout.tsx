import './globals.css'
import { Inter } from 'next/font/google'
import { AuthProvider } from '../contexts/AuthContext'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Plum OPD Claim Adjudication',
  description: 'AI-powered outpatient claim processing system',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <div className="min-h-screen bg-insurance-light">
            {children}
          </div>
        </AuthProvider>
      </body>
    </html>
  )
}
