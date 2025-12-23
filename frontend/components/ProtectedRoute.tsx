'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';

export default function ProtectedRoute({
    children,
    requiredRole,
}: {
    children: React.ReactNode;
    requiredRole?: string;
}) {
    const { user, isLoading, initializeAuth } = useAuth();
    const router = useRouter();
    const [authChecked, setAuthChecked] = useState(false);

    // Trigger auth check on mount
    useEffect(() => {
        const checkAuth = async () => {
            await initializeAuth();
            setAuthChecked(true);
        };
        checkAuth();
    }, [initializeAuth]);

    // Redirect after auth check completes
    useEffect(() => {
        if (authChecked && !isLoading) {
            if (!user) {
                router.push('/login');
            } else if (requiredRole && user.role !== requiredRole) {
                router.push('/unauthorized');
            }
        }
    }, [authChecked, user, isLoading, requiredRole, router]);

    // Show loading while checking auth
    if (!authChecked || isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center gradient-bg">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
                    <p className="text-white">Loading...</p>
                </div>
            </div>
        );
    }

    // Don't render if not authenticated or wrong role
    if (!user || (requiredRole && user.role !== requiredRole)) {
        return null;
    }

    return <>{children}</>;
}
