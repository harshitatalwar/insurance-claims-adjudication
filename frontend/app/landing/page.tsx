'use client'

import { useRouter } from 'next/navigation'
import { Shield, FileText, Zap, CheckCircle, ArrowRight } from 'lucide-react'
import Link from 'next/link'

export default function LandingPage() {
    const router = useRouter()

    return (
        <div className="min-h-screen bg-gradient-to-br from-plum-50 via-white to-blue-50">
            {/* Header */}
            <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <div className="flex items-center space-x-2">
                            <div className="w-10 h-10 bg-plum-600 rounded-full flex items-center justify-center">
                                <span className="text-white font-bold text-lg">P</span>
                            </div>
                            <span className="text-xl font-bold text-gray-900">Plum Insurance</span>
                        </div>
                        <div className="flex items-center space-x-4">
                            <Link href="/login" className="text-gray-600 hover:text-gray-900 font-medium">
                                Login
                            </Link>
                            <Link
                                href="/register"
                                className="insurance-button px-6 py-2"
                            >
                                Get Started
                            </Link>
                        </div>
                    </div>
                </div>
            </header>

            {/* Hero Section */}
            <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                    <div>
                        <h1 className="text-5xl font-bold text-gray-900 mb-6">
                            AI-Powered OPD Claims
                            <span className="text-plum-600"> Made Simple</span>
                        </h1>
                        <p className="text-xl text-gray-600 mb-8">
                            Submit your outpatient claims in seconds. Our AI extracts data from your documents and processes claims instantly with 95% accuracy.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4">
                            <button
                                onClick={() => router.push('/register')}
                                className="insurance-button px-8 py-4 text-lg font-semibold flex items-center justify-center"
                            >
                                Start Your Claim
                                <ArrowRight className="ml-2 w-5 h-5" />
                            </button>
                            <button
                                onClick={() => router.push('/login')}
                                className="px-8 py-4 text-lg font-semibold border-2 border-insurance-blue text-insurance-blue rounded-md hover:bg-blue-50 transition-colors"
                            >
                                Sign In
                            </button>
                        </div>
                        <div className="mt-8 flex items-center space-x-6 text-sm text-gray-600">
                            <div className="flex items-center">
                                <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
                                <span>Instant Processing</span>
                            </div>
                            <div className="flex items-center">
                                <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
                                <span>95% Accuracy</span>
                            </div>
                            <div className="flex items-center">
                                <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
                                <span>24/7 Support</span>
                            </div>
                        </div>
                    </div>

                    <div className="relative">
                        <div className="insurance-card p-8">
                            <div className="space-y-4">
                                <div className="flex items-center space-x-3 p-4 bg-green-50 border border-green-200 rounded-lg">
                                    <CheckCircle className="w-8 h-8 text-green-600" />
                                    <div>
                                        <p className="font-semibold text-gray-900">Claim Approved</p>
                                        <p className="text-sm text-gray-600">₹5,000 processed in 2 minutes</p>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                                    <Zap className="w-8 h-8 text-blue-600" />
                                    <div>
                                        <p className="font-semibold text-gray-900">AI Extraction</p>
                                        <p className="text-sm text-gray-600">Auto-fill from your documents</p>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-3 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                                    <Shield className="w-8 h-8 text-plum-600" />
                                    <div>
                                        <p className="font-semibold text-gray-900">Secure & Private</p>
                                        <p className="text-sm text-gray-600">Bank-level encryption</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="bg-white py-20">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-bold text-gray-900 mb-4">How It Works</h2>
                        <p className="text-xl text-gray-600">Three simple steps to get your claim approved</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <div className="text-center">
                            <div className="w-16 h-16 bg-plum-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <FileText className="w-8 h-8 text-plum-600" />
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">1. Upload Documents</h3>
                            <p className="text-gray-600">
                                Upload your prescription, bills, and diagnostic reports. Our AI extracts all the data automatically.
                            </p>
                        </div>

                        <div className="text-center">
                            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Zap className="w-8 h-8 text-insurance-blue" />
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">2. AI Processing</h3>
                            <p className="text-gray-600">
                                Our intelligent system validates your claim against policy terms and checks for fraud in real-time.
                            </p>
                        </div>

                        <div className="text-center">
                            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <CheckCircle className="w-8 h-8 text-green-600" />
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">3. Instant Decision</h3>
                            <p className="text-gray-600">
                                Get approval in minutes, not days. Track your claim status and receive notifications instantly.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Stats Section */}
            <section className="py-20">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                        <div className="text-center">
                            <p className="text-4xl font-bold text-plum-600 mb-2">10x</p>
                            <p className="text-gray-600">Faster Processing</p>
                        </div>
                        <div className="text-center">
                            <p className="text-4xl font-bold text-plum-600 mb-2">95%</p>
                            <p className="text-gray-600">Accuracy Rate</p>
                        </div>
                        <div className="text-center">
                            <p className="text-4xl font-bold text-plum-600 mb-2">₹50k</p>
                            <p className="text-gray-600">Annual Coverage</p>
                        </div>
                        <div className="text-center">
                            <p className="text-4xl font-bold text-plum-600 mb-2">24/7</p>
                            <p className="text-gray-600">Support Available</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="bg-gradient-to-r from-plum-600 to-blue-600 py-20">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                    <h2 className="text-3xl font-bold text-white mb-4">
                        Ready to Experience Hassle-Free Claims?
                    </h2>
                    <p className="text-xl text-white/90 mb-8">
                        Join thousands of satisfied policy holders who trust Plum Insurance for their OPD claims.
                    </p>
                    <button
                        onClick={() => router.push('/register')}
                        className="bg-white text-plum-600 px-8 py-4 text-lg font-semibold rounded-md hover:bg-gray-100 transition-colors inline-flex items-center"
                    >
                        Get Started Free
                        <ArrowRight className="ml-2 w-5 h-5" />
                    </button>
                </div>
            </section>

            {/* Footer */}
            <footer className="bg-gray-900 text-white py-12">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                        <div>
                            <div className="flex items-center space-x-2 mb-4">
                                <div className="w-8 h-8 bg-plum-600 rounded-full flex items-center justify-center">
                                    <span className="text-white font-bold">P</span>
                                </div>
                                <span className="text-lg font-bold">Plum Insurance</span>
                            </div>
                            <p className="text-gray-400 text-sm">
                                AI-powered OPD claim processing for modern healthcare.
                            </p>
                        </div>
                        <div>
                            <h4 className="font-semibold mb-4">Product</h4>
                            <ul className="space-y-2 text-sm text-gray-400">
                                <li><a href="#" className="hover:text-white">Features</a></li>
                                <li><a href="#" className="hover:text-white">Pricing</a></li>
                                <li><a href="#" className="hover:text-white">FAQ</a></li>
                            </ul>
                        </div>
                        <div>
                            <h4 className="font-semibold mb-4">Company</h4>
                            <ul className="space-y-2 text-sm text-gray-400">
                                <li><a href="#" className="hover:text-white">About</a></li>
                                <li><a href="#" className="hover:text-white">Blog</a></li>
                                <li><a href="#" className="hover:text-white">Careers</a></li>
                            </ul>
                        </div>
                        <div>
                            <h4 className="font-semibold mb-4">Legal</h4>
                            <ul className="space-y-2 text-sm text-gray-400">
                                <li><a href="#" className="hover:text-white">Privacy</a></li>
                                <li><a href="#" className="hover:text-white">Terms</a></li>
                                <li><a href="#" className="hover:text-white">Security</a></li>
                            </ul>
                        </div>
                    </div>
                    <div className="border-t border-gray-800 mt-8 pt-8 text-center text-sm text-gray-400">
                        <p>&copy; 2024 Plum Insurance. All rights reserved.</p>
                    </div>
                </div>
            </footer>
        </div>
    )
}
