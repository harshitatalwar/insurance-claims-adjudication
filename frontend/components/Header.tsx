'use client'

import Link from 'next/link'
import { Bell, LogOut } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export default function Header() {
    const { user, policyHolder, logout } = useAuth()

    return (
        <header className="bg-white border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-16">
                    {/* Logo */}
                    <div className="flex items-center space-x-2">
                        <div className="w-10 h-10 bg-plum-600 rounded-full flex items-center justify-center">
                            <span className="text-white font-bold text-lg">P</span>
                        </div>
                        <span className="text-xl font-bold text-gray-900">Plum Insurance</span>
                    </div>

                    {/* Navigation */}
                    <nav className="hidden md:flex space-x-8">
                        <Link href="/" className="text-insurance-blue font-medium">Submit Claim</Link>
                        <Link href="/claims" className="text-gray-500 hover:text-gray-700">Track Claims</Link>
                        <Link href="/policy-details" className="text-gray-500 hover:text-gray-700">Policy Details</Link>
                        <Link href="/dashboard" className="text-gray-500 hover:text-gray-700">Dashboard</Link>
                    </nav>

                    {/* User Menu */}
                    <div className="flex items-center space-x-4">
                        {user ? (
                            <>
                                <span className="text-sm text-gray-600 hidden md:block">
                                    {policyHolder?.policy_holder_id || user.email}
                                </span>
                                <button className="p-2 text-gray-500 hover:text-gray-700">
                                    <Bell className="w-5 h-5" />
                                </button>
                                <button
                                    onClick={logout}
                                    className="p-2 text-gray-500 hover:text-gray-700"
                                    title="Logout"
                                >
                                    <LogOut className="w-5 h-5" />
                                </button>
                            </>
                        ) : (
                            <Link href="/login" className="insurance-button px-4 py-2">
                                Sign In
                            </Link>
                        )}
                    </div>
                </div>
            </div>
        </header>
    )
}
