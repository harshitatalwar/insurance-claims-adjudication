'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '../../../contexts/AuthContext'
import { useRouter, useSearchParams } from 'next/navigation'
import axios from 'axios'
import { ArrowLeft } from 'lucide-react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

interface ClaimData {
    claim_id: string
    status: string
    decision?: string
    notes?: string
    next_steps?: string
    approved_amount?: number
    claimed_amount?: number
    rejection_reasons?: string[]
    confidence_score?: number
    processed_at?: string
}

export default function Step3ClaimStatusPage() {
    const { user, token, isLoading } = useAuth()
    const router = useRouter()
    const searchParams = useSearchParams()

    const claimId = searchParams.get('claim_id')
    const [claimData, setClaimData] = useState<ClaimData | null>(null)
    const [loading, setLoading] = useState(true)

    // Redirect if not authenticated
    useEffect(() => {
        if (!isLoading && !user) {
            router.push('/login')
        }
    }, [user, isLoading, router])

    // Redirect if no claim ID
    useEffect(() => {
        if (!claimId) {
            router.push('/upload/step1')
        }
    }, [claimId, router])

    // Fetch claim data
    useEffect(() => {
        if (claimId && token) {
            fetchClaimData()
        }
    }, [claimId, token])

    // Real-time updates via SSE
    useEffect(() => {
        if (!claimId || !token) return

        const eventSource = new EventSource(`${API_BASE_URL}/api/claims/${claimId}/stream`)

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)

                if (data.type === 'claim_decision') {
                    console.log("✅ Claim adjudicated:", data.decision)
                    fetchClaimData()
                }
            } catch (e) {
                console.error("Error parsing SSE data:", e)
            }
        }

        return () => {
            eventSource.close()
        }
    }, [claimId, token])

    const fetchClaimData = async () => {
        try {
            const response = await axios.get(
                `${API_BASE_URL}/api/claims/${claimId}`,
                { headers: { Authorization: `Bearer ${token}` } }
            )
            setClaimData(response.data)
        } catch (err) {
            console.error('Failed to load claim data:', err)
        } finally {
            setLoading(false)
        }
    }

    if (isLoading || loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-xl">Loading...</div>
            </div>
        )
    }

    if (!user) {
        return null
    }

    const hasDecision = claimData && (claimData.decision || claimData.status === 'approved' || claimData.status === 'rejected' || claimData.status === 'under_review')

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
            <div className="max-w-4xl mx-auto">
                {/* Progress Indicator */}
                <div className="mb-8">
                    <div className="flex items-center justify-center gap-4">
                        <div className="flex items-center">
                            <div className="w-10 h-10 rounded-full bg-green-500 text-white flex items-center justify-center font-bold">
                                ✓
                            </div>
                            <span className="ml-2 text-gray-600">Upload Documents</span>
                        </div>
                        <div className="w-16 h-1 bg-green-500"></div>
                        <div className="flex items-center">
                            <div className="w-10 h-10 rounded-full bg-green-500 text-white flex items-center justify-center font-bold">
                                ✓
                            </div>
                            <span className="ml-2 text-gray-600">View Documents</span>
                        </div>
                        <div className="w-16 h-1 bg-blue-600"></div>
                        <div className="flex items-center">
                            <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold">
                                3
                            </div>
                            <span className="ml-2 font-semibold text-blue-600">Claim Status</span>
                        </div>
                    </div>
                </div>

                {/* Back Button */}
                <button
                    onClick={() => router.push(`/upload/step2?claim_id=${claimId}`)}
                    className="mb-6 flex items-center gap-2 text-blue-600 hover:text-blue-700 font-semibold"
                >
                    <ArrowLeft className="w-5 h-5" />
                    Back to Documents
                </button>

                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-4xl font-bold text-gray-900 mb-2">Claim Adjudication Status</h1>
                    <p className="text-gray-600">
                        View the status and decision for your claim.
                    </p>
                    {claimId && (
                        <p className="text-sm text-gray-500 mt-2">
                            Claim ID: <span className="font-mono font-semibold">{claimId}</span>
                        </p>
                    )}
                </div>

                {/* Claim Status */}
                {hasDecision ? (
                    <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
                        <h2 className="text-2xl font-bold mb-6">Adjudication Results</h2>

                        <div className="space-y-4">
                            {/* Status Badge */}
                            <div className="flex items-center gap-4">
                                <span className="text-sm font-medium text-gray-600">Status:</span>
                                <span className={`px-4 py-2 rounded-full font-semibold text-sm ${claimData.status === 'approved' || claimData.decision === 'APPROVED'
                                    ? 'bg-green-100 text-green-800'
                                    : claimData.status === 'rejected' || claimData.decision === 'REJECTED'
                                        ? 'bg-red-100 text-red-800'
                                        : claimData.status === 'under_review' || claimData.decision === 'MANUAL_REVIEW'
                                            ? 'bg-yellow-100 text-yellow-800'
                                            : claimData.decision === 'PARTIAL'
                                                ? 'bg-blue-100 text-blue-800'
                                                : 'bg-gray-100 text-gray-800'
                                    }`}>
                                    {claimData.decision || claimData.status.toUpperCase()}
                                </span>
                            </div>

                            {/* Approved Amount */}
                            {claimData.approved_amount !== undefined && claimData.approved_amount > 0 && (
                                <div className="flex items-center gap-4">
                                    <span className="text-sm font-medium text-gray-600">Approved Amount:</span>
                                    <span className="text-2xl font-bold text-green-600">
                                        ₹{claimData.approved_amount.toFixed(2)}
                                    </span>
                                    {claimData.claimed_amount && (
                                        <span className="text-sm text-gray-500">
                                            (Claimed: ₹{claimData.claimed_amount.toFixed(2)})
                                        </span>
                                    )}
                                </div>
                            )}

                            {/* Notes */}
                            {claimData.notes && (
                                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                                    <h4 className="font-semibold text-sm text-blue-900 mb-2">📝 Notes:</h4>
                                    <p className="text-sm text-blue-800 whitespace-pre-wrap">{claimData.notes}</p>
                                </div>
                            )}

                            {/* Next Steps */}
                            {claimData.next_steps && (
                                <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
                                    <h4 className="font-semibold text-sm text-purple-900 mb-2">🎯 Next Steps:</h4>
                                    <p className="text-sm text-purple-800 whitespace-pre-wrap">{claimData.next_steps}</p>
                                </div>
                            )}

                            {/* Rejection Reasons */}
                            {claimData.rejection_reasons && claimData.rejection_reasons.length > 0 && (
                                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                                    <h4 className="font-semibold text-sm text-red-900 mb-2">❌ Rejection Reasons:</h4>
                                    <ul className="list-disc list-inside space-y-1">
                                        {claimData.rejection_reasons.map((reason, index) => (
                                            <li key={index} className="text-sm text-red-800">{reason}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Processed At */}
                            {claimData.processed_at && (
                                <div className="flex items-center gap-4 text-sm text-gray-500">
                                    <span>Processed at:</span>
                                    <span>{new Date(claimData.processed_at).toLocaleString()}</span>
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="bg-white rounded-2xl shadow-xl p-12 text-center">
                        <div className="text-6xl mb-4">⏳</div>
                        <h3 className="text-xl font-semibold text-gray-700 mb-2">Processing Your Claim</h3>
                        <p className="text-gray-500 mb-6">
                            Your claim is being reviewed. This may take a few moments.
                        </p>
                        <div className="animate-pulse flex justify-center">
                            <div className="h-2 w-64 bg-blue-200 rounded"></div>
                        </div>
                    </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-4">
                    <button
                        onClick={() => {
                            localStorage.removeItem('current_claim_id')
                            router.push('/upload/step1')
                        }}
                        className="flex-1 bg-blue-600 text-white py-4 px-6 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
                    >
                        📤 Upload More Documents
                    </button>
                    <button
                        onClick={() => router.push('/dashboard')}
                        className="flex-1 bg-gray-600 text-white py-4 px-6 rounded-lg font-semibold hover:bg-gray-700 transition-colors"
                    >
                        🏠 Go to Dashboard
                    </button>
                </div>
            </div>
        </div>
    )
}
