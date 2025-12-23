'use client'

import { AuthProvider } from '../../contexts/AuthContext'

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
    return (
        <AuthProvider>
            <div className="min-h-screen bg-insurance-light">
                {children}
            </div>
        </AuthProvider>
    )
}
