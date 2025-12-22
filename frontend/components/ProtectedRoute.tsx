'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';

export default function ProtectedRoute({
    children,
    requiredRole,
}: {
    children: React.ReactNode;
    requiredRole?: string;
}) {
    const { user, isLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!isLoading) {
            if (!user) {
                router.push('/login');
            } else if (requiredRole && user.role !== requiredRole) {
                router.push('/unauthorized');
            }
        }
    }, [user, isLoading, requiredRole, router]);

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center gradient-bg">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
                    <p className="text-white">Loading...</p>
                </div>
            </div>
        );
    }

    if (!user || (requiredRole && user.role !== requiredRole)) {
        return null;
    }

    return <>{children}</>;
}
