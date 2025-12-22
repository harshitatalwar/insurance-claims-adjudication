'use client'

import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../../../contexts/AuthContext'
import { useRouter } from 'next/navigation'
import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export default function Step1UploadPage() {
    const { user, policyHolder, token, isLoading } = useAuth()
    const router = useRouter()

    const urlClaimId = typeof window !== 'undefined'
        ? new URLSearchParams(window.location.search).get('claim_id')
        : null
    const [claimId, setClaimId] = useState<string | null>(() => {
        if (typeof window !== 'undefined') {
            const cached = localStorage.getItem('current_claim_id')
            if (cached) return cached
        }
        return urlClaimId
    })

    const [selectedFiles, setSelectedFiles] = useState<File[]>([])
    const [documentType, setDocumentType] = useState('auto')
    const [uploading, setUploading] = useState(false)
    const [uploadComplete, setUploadComplete] = useState(false)
    const [error, setError] = useState('')
    const [dragActive, setDragActive] = useState(false)

    const claimCreationAttempted = useRef(false)

    // Redirect if not authenticated
    useEffect(() => {
        if (!isLoading && !user) {
            router.push('/login')
        }
    }, [user, isLoading, router])

    // Auto-create claim
    useEffect(() => {
        if (claimId) {
            console.log('📋 Resuming existing claim:', claimId)
            return
        }

        if (policyHolder && !claimCreationAttempted.current) {
            claimCreationAttempted.current = true
            createClaim()
        }
    }, [policyHolder, claimId])

    // Auto-redirect to step 2 after upload completes
    useEffect(() => {
        if (uploadComplete && claimId) {
            const timer = setTimeout(() => {
                router.push(`/upload/step2?claim_id=${claimId}`)
            }, 10000) // 10 seconds

            return () => clearTimeout(timer)
        }
    }, [uploadComplete, claimId, router])

    const createClaim = async () => {
        if (!policyHolder || !policyHolder.policy_holder_id) {
            setError('Authentication error. Please log out and log in again.')
            return
        }

        try {
            const response = await axios.post(
                `${API_BASE_URL}/api/claims/`,
                {
                    policy_holder_id: policyHolder.policy_holder_id,
                    claimed_amount: 0.0,
                    treatment_type: 'consultation',
                    provider_network: false,
                    treatment_date: new Date().toISOString()
                },
                {
                    headers: { Authorization: `Bearer ${token}` }
                }
            )
            const newClaimId = response.data.claim_id

            setClaimId(newClaimId)
            localStorage.setItem('current_claim_id', newClaimId)

            const url = new URL(window.location.href)
            url.searchParams.set('claim_id', newClaimId)
            window.history.replaceState({}, '', url.toString())

            console.log('✅ Auto-created claim:', newClaimId)
        } catch (err: any) {
            setError(`Failed to initialize claim: ${err.response?.data?.detail || err.message}`)
        }
    }

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true)
        } else if (e.type === 'dragleave') {
            setDragActive(false)
        }
    }

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setDragActive(false)

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const newFiles = Array.from(e.dataTransfer.files)
            setSelectedFiles(prev => [...prev, ...newFiles])
            setError('')
        }
    }

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const newFiles = Array.from(e.target.files)
            setSelectedFiles(prev => [...prev, ...newFiles])
            setError('')
        }
    }

    const removeFile = (index: number) => {
        setSelectedFiles(prev => prev.filter((_, i) => i !== index))
    }

    const uploadAllDocuments = async () => {
        if (selectedFiles.length === 0 || !claimId) {
            setError('Please select at least one file')
            return
        }

        setUploading(true)
        setError('')

        try {
            for (let i = 0; i < selectedFiles.length; i++) {
                const file = selectedFiles[i]

                const presignedResponse = await axios.post(
                    `${API_BASE_URL}/api/documents/upload`,
                    {
                        claim_id: claimId,
                        filename: file.name,
                        document_type: documentType
                    },
                    {
                        headers: { Authorization: `Bearer ${token}` }
                    }
                )

                const { file_id, upload_url } = presignedResponse.data

                await axios.put(upload_url, file, {
                    headers: {
                        'Content-Type': file.type || 'application/octet-stream'
                    }
                })

                await axios.post(
                    `${API_BASE_URL}/api/documents/${file_id}/process`,
                    {},
                    {
                        headers: { Authorization: `Bearer ${token}` }
                    }
                )
            }

            setUploadComplete(true)
            setSelectedFiles([])
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Upload failed')
        } finally {
            setUploading(false)
        }
    }

    if (isLoading) {
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
                            <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold">
                                1
                            </div>
                            <span className="ml-2 font-semibold text-blue-600">Upload Documents</span>
                        </div>
                        <div className="w-16 h-1 bg-gray-300"></div>
                        <div className="flex items-center">
                            <div className="w-10 h-10 rounded-full bg-gray-300 text-gray-600 flex items-center justify-center font-bold">
                                2
                            </div>
                            <span className="ml-2 text-gray-500">View Documents</span>
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

                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-4xl font-bold text-gray-900 mb-2">Upload Medical Documents</h1>
                    <p className="text-gray-600">
                        Welcome, {user.full_name}! Upload your prescription, bills, or medical reports.
                    </p>
                    {claimId && (
                        <p className="text-sm text-gray-500 mt-2">
                            Claim ID: <span className="font-mono font-semibold">{claimId}</span>
                        </p>
                    )}
                </div>

                {/* Upload Complete Message */}
                {uploadComplete && (
                    <div className="bg-green-50 border border-green-200 rounded-xl p-6 mb-8">
                        <div className="flex items-center gap-3">
                            <div className="text-4xl">✅</div>
                            <div>
                                <h3 className="text-xl font-bold text-green-800">Upload Successful!</h3>
                                <p className="text-green-700">Redirecting to view your documents...</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Upload Section */}
                {!uploadComplete && (
                    <div className="bg-white rounded-2xl shadow-xl p-8">
                        <h2 className="text-2xl font-bold mb-6">Upload New Document</h2>

                        {/* Drag & Drop Zone */}
                        <div
                            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all ${dragActive
                                ? 'border-blue-500 bg-blue-50'
                                : 'border-gray-300 hover:border-blue-400'
                                }`}
                            onDragEnter={handleDrag}
                            onDragLeave={handleDrag}
                            onDragOver={handleDrag}
                            onDrop={handleDrop}
                        >
                            <div className="space-y-4">
                                <div className="text-6xl">📄</div>
                                <div>
                                    <p className="text-lg font-semibold text-gray-700">
                                        Drag and drop your file here
                                    </p>
                                    <p className="text-sm text-gray-500">or</p>
                                </div>
                                <label className="inline-block">
                                    <input
                                        type="file"
                                        multiple
                                        onChange={handleFileChange}
                                        className="hidden"
                                        accept=".pdf,.jpg,.jpeg,.png"
                                    />
                                    <span className="cursor-pointer bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors inline-block">
                                        Browse Files
                                    </span>
                                </label>
                                {selectedFiles.length > 0 && (
                                    <div className="mt-4 space-y-2">
                                        <p className="text-sm font-semibold text-gray-700">
                                            Selected Files ({selectedFiles.length}):
                                        </p>
                                        {selectedFiles.map((file, index) => (
                                            <div key={index} className="flex items-center justify-between bg-green-50 p-2 rounded">
                                                <span className="text-sm text-green-700">
                                                    ✓ {file.name} ({(file.size / 1024).toFixed(2)} KB)
                                                </span>
                                                <button
                                                    onClick={() => removeFile(index)}
                                                    className="text-red-600 hover:text-red-800 text-sm"
                                                >
                                                    ✕
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Document Type Selector */}
                        <div className="mt-6">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Document Type
                            </label>
                            <select
                                value={documentType}
                                onChange={(e) => setDocumentType(e.target.value)}
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            >
                                <option value="auto">Auto-detect</option>
                                <option value="prescription">Prescription</option>
                                <option value="bill">Medical Bill</option>
                                <option value="report">Lab Report</option>
                                <option value="pharmacy_bill">Pharmacy Bill</option>
                                <option value="consultation_note">Consultation Note</option>
                                <option value="other">Other</option>
                            </select>
                        </div>

                        {/* Upload Button */}
                        <button
                            onClick={uploadAllDocuments}
                            disabled={selectedFiles.length === 0 || uploading || !claimId}
                            className="w-full mt-6 bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-4 px-6 rounded-lg font-semibold text-lg hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-400 disabled:cursor-not-allowed transition-all shadow-lg"
                        >
                            {uploading ? '📤 Uploading...' : `📤 Upload ${selectedFiles.length} File(s)`}
                        </button>

                        {/* Error Message */}
                        {error && (
                            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                                <p className="text-red-800 text-sm">❌ {error}</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}
