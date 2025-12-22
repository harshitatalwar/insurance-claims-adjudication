'use client'

import { useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { User, Lock, Mail } from 'lucide-react'
import Link from 'next/link'

export default function LoginPage() {
    const { login } = useAuth()
    const [formData, setFormData] = useState({
        email: '',
        password: ''
    })
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        if (formData.password.length < 6 || formData.password.length > 12) {
            setError('Password must be between 6 and 12 characters')
            return
        }

        setIsLoading(true)

        try {
            await login(formData.email, formData.password)
            // Redirect handled by AuthContext
        } catch (err: any) {
            setError(err.message || 'Login failed')
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-insurance-light flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full">
                {/* Logo and Title */}
                <div className="text-center mb-8">
                    <div className="w-16 h-16 bg-plum-600 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span className="text-white font-bold text-2xl">P</span>
                    </div>
                    <h2 className="text-3xl font-bold text-gray-900">Plum Insurance</h2>
                    <p className="mt-2 text-sm text-gray-600">Sign in to submit your OPD claims</p>
                </div>

                {/* Login Card */}
                <div className="insurance-card">
                    <form onSubmit={handleSubmit} className="space-y-6">
                        {error && (
                            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                                <p className="text-sm text-red-800">{error}</p>
                            </div>
                        )}

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Email Address
                            </label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <Mail className="h-5 w-5 text-gray-400" />
                                </div>
                                <input
                                    type="email"
                                    required
                                    className="insurance-input w-full pl-10"
                                    placeholder="you@example.com"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Password
                            </label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <Lock className="h-5 w-5 text-gray-400" />
                                </div>
                                <input
                                    type="password"
                                    required
                                    className="insurance-input w-full pl-10"
                                    placeholder="••••••••"
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                />
                            </div>
                        </div>

                        <div className="flex items-center justify-between">
                            <div className="flex items-center">
                                <input
                                    id="remember-me"
                                    name="remember-me"
                                    type="checkbox"
                                    className="h-4 w-4 text-insurance-blue focus:ring-insurance-blue border-gray-300 rounded"
                                />
                                <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
                                    Remember me
                                </label>
                            </div>

                            <div className="text-sm">
                                <a href="#" className="font-medium text-insurance-blue hover:text-blue-700">
                                    Forgot password?
                                </a>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="insurance-button w-full py-3 text-base font-medium disabled:opacity-50"
                        >
                            {isLoading ? 'Signing in...' : 'Sign in'}
                        </button>
                    </form>

                    <div className="mt-6">
                        <div className="relative">
                            <div className="absolute inset-0 flex items-center">
                                <div className="w-full border-t border-gray-300"></div>
                            </div>
                            <div className="relative flex justify-center text-sm">
                                <span className="px-2 bg-white text-gray-500">Or</span>
                            </div>
                        </div>

                        <div className="mt-6 text-center">
                            <p className="text-sm text-gray-600">
                                Don't have an account?{' '}
                                <Link href="/register" className="font-medium text-insurance-blue hover:text-blue-700">
                                    Sign up
                                </Link>
                            </p>
                        </div>

                        <div className="mt-4 text-center">
                            <Link href="/landing" className="text-sm text-insurance-blue hover:text-blue-700">
                                ← Back to home
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
