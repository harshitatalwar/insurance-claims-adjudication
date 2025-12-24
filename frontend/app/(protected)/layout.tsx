'use client'

import { useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { useRouter } from 'next/navigation'

function AuthGuard({ children }: { children: React.ReactNode }) {
    const { user, isLoading, initializeAuth, isInitialized } = useAuth()
    const router = useRouter()

    useEffect(() => {
        initializeAuth()
    }, [])

    useEffect(() => {
        if (isInitialized && !user && !isLoading) {
            router.push('/login')
        }
    }, [user, isLoading, isInitialized, router])

    if (isLoading || !isInitialized) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-gray-600 font-medium">Loading session...</p>
                </div>
            </div>
        )
    }

    if (!user) {
        return null
    }

    return <>{children}</>
}

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="min-h-screen bg-insurance-light">
            <AuthGuard>
                {children}
            </AuthGuard>
        </div>
    )
}
