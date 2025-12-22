'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '../../../contexts/AuthContext'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { Check, ArrowLeft } from 'lucide-react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

interface UploadedDocument {
    file_id: string
    filename: string
    document_type: string
    status: string
    uploaded_at?: string
    confidence_score?: number
    extracted_data?: any
}

export default function Step2DocumentsPage() {
    const { user, token, isLoading } = useAuth()
    const router = useRouter()

    const claimId = typeof window !== 'undefined'
        ? new URLSearchParams(window.location.search).get('claim_id')
        : null
    const [documents, setDocuments] = useState<UploadedDocument[]>([])
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

    // Fetch documents
    useEffect(() => {
        if (claimId && token) {
            fetchDocuments()
        }
    }, [claimId, token])

    // Auto-redirect to step 3 after 10 seconds
    useEffect(() => {
        if (documents.length > 0 && claimId) {
            const timer = setTimeout(() => {
                router.push(`/upload/step3?claim_id=${claimId}`)
            }, 10000) // 10 seconds

            return () => clearTimeout(timer)
        }
    }, [documents, claimId, router])

    // Real-time updates via SSE
    useEffect(() => {
        if (!claimId || !token) return

        const eventSource = new EventSource(`${API_BASE_URL}/api/claims/${claimId}/stream`)

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)

                if (data.type === 'document_update') {
                    setDocuments(prev => {
                        const existingIndex = prev.findIndex(doc => doc.file_id === data.file_id)

                        if (existingIndex >= 0) {
                            return prev.map(doc =>
                                doc.file_id === data.file_id
                                    ? { ...doc, status: data.status, extracted_data: data.extracted_data }
                                    : doc
                            )
                        } else {
                            return [...prev, {
                                file_id: data.file_id,
                                filename: data.filename || "Unknown",
                                document_type: data.document_type || "auto",
                                status: data.status,
                                extracted_data: data.extracted_data
                            }]
                        }
                    })
                }
            } catch (e) {
                console.error("Error parsing SSE data:", e)
            }
        }

        return () => {
            eventSource.close()
        }
    }, [claimId, token])

    const fetchDocuments = async () => {
        try {
            const response = await axios.get(
                `${API_BASE_URL}/api/documents/status?claim_id=${claimId}`,
                { headers: { Authorization: `Bearer ${token}` } }
            )
            setDocuments(response.data)
        } catch (err) {
            console.error('Failed to load documents:', err)
        } finally {
            setLoading(false)
        }
    }

    const getStatusDisplay = (status: string) => {
        switch (status) {
            case 'uploaded':
                return { text: 'Queued', icon: '⏳', color: 'text-gray-500' }
            case 'processing':
                return { text: 'Extracting Information...', icon: '⚙️', color: 'text-blue-600 animate-pulse' }
            case 'processed':
                return { text: 'Done', icon: '✅', color: 'text-green-600' }
            case 'failed':
                return { text: 'Failed', icon: '❌', color: 'text-red-600' }
            default:
                return { text: 'Waiting...', icon: '🕒', color: 'text-gray-400' }
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
                        <div className="w-16 h-1 bg-blue-600"></div>
                        <div className="flex items-center">
                            <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold">
                                2
                            </div>
                            <span className="ml-2 font-semibold text-blue-600">View Documents</span>
                        </div>
                        <div className="w-16 h-1 bg-gray-300"></div>
                        <div className="flex items-center">
                            <div className="w-10 h-10 rounded-full bg-gray-300 text-gray-600 flex items-center justify-center font-bold">
                                3
                            </div>
                            <span className="ml-2 text-gray-500">Claim Status</span>
                        </div>
                    </div>
                </div>

                {/* Back Button */}
                <button
                    onClick={() => router.push(`/upload/step1?claim_id=${claimId}`)}
                    className="mb-6 flex items-center gap-2 text-blue-600 hover:text-blue-700 font-semibold"
                >
                    <ArrowLeft className="w-5 h-5" />
                    Back to Upload
                </button>

                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-4xl font-bold text-gray-900 mb-2">Uploaded Documents</h1>
                    <p className="text-gray-600">
                        Review your uploaded documents and their processing status.
                    </p>
                    {claimId && (
                        <p className="text-sm text-gray-500 mt-2">
                            Claim ID: <span className="font-mono font-semibold">{claimId}</span>
                        </p>
                    )}
                </div>

                {/* Documents List */}
                {documents.length > 0 ? (
                    <div className="bg-white rounded-2xl shadow-xl p-8">
                        <h2 className="text-2xl font-bold mb-6">Your Documents</h2>
                        <div className="space-y-4">
                            {documents.map((doc) => {
                                const statusInfo = getStatusDisplay(doc.status)

                                return (
                                    <div
                                        key={doc.file_id}
                                        className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
                                    >
                                        <div className="flex justify-between items-start mb-4">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-3 mb-2">
                                                    <h3 className="font-semibold text-lg text-gray-900">
                                                        {doc.filename}
                                                    </h3>

                                                    <span className={`text-sm flex items-center gap-2 ${statusInfo.color}`}>
                                                        <span>{statusInfo.icon}</span>
                                                        <span className="font-medium">{statusInfo.text}</span>
                                                    </span>
                                                </div>

                                                <p className="text-sm text-gray-500">
                                                    Type: <span className="font-medium">{doc.document_type}</span>
                                                </p>
                                            </div>

                                            {doc.status === 'processed' && (
                                                <div className="bg-green-100 p-2 rounded-full">
                                                    <Check className="w-5 h-5 text-green-600" />
                                                </div>
                                            )}
                                        </div>

                                        {doc.status === 'processed' && doc.extracted_data && (
                                            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                                                <h4 className="font-semibold text-sm text-gray-700 mb-2">
                                                    Extracted Data:
                                                </h4>
                                                <pre className="text-xs text-gray-600 overflow-auto max-h-64">
                                                    {JSON.stringify(doc.extracted_data, null, 2)}
                                                </pre>
                                                {doc.confidence_score && (
                                                    <p className="mt-2 text-sm text-gray-600">
                                                        Confidence: <span className="font-semibold">{(doc.confidence_score * 100).toFixed(1)}%</span>
                                                    </p>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )
                            })}
                        </div>

                        <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                            <p className="text-blue-800 text-center">
                                ⏳ Processing your documents... You'll be redirected to view the claim status shortly.
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="bg-white rounded-2xl shadow-xl p-12 text-center">
                        <div className="text-6xl mb-4">📄</div>
                        <h3 className="text-xl font-semibold text-gray-700 mb-2">No documents uploaded yet</h3>
                        <p className="text-gray-500 mb-6">Upload your medical documents to get started.</p>
                        <button
                            onClick={() => router.push(`/upload/step1?claim_id=${claimId}`)}
                            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            Upload Documents
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}
