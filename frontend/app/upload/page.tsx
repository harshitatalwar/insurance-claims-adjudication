'use client'

import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { useRouter, useSearchParams } from 'next/navigation'
import axios from 'axios'
import { Check } from 'lucide-react'

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

export default function UploadPage() {
    const { user, policyHolder, token, isLoading } = useAuth()
    const router = useRouter()
    const searchParams = useSearchParams()

    // 1. Initialize state from localStorage first, then URL (prevents duplicate claims on refresh)
    const urlClaimId = searchParams.get('claim_id')
    const [claimId, setClaimId] = useState<string | null>(() => {
        // Try localStorage first (most reliable)
        if (typeof window !== 'undefined') {
            const cached = localStorage.getItem('current_claim_id')
            if (cached) return cached
        }
        // Fallback to URL parameter
        return urlClaimId
    })

    // Multi-file support: Changed from single File to array
    const [selectedFiles, setSelectedFiles] = useState<File[]>([])
    const [documentType, setDocumentType] = useState('auto')
    const [uploading, setUploading] = useState(false)
    const [processing, setProcessing] = useState(false)
    const [documents, setDocuments] = useState<UploadedDocument[]>([])
    const [error, setError] = useState('')
    const [dragActive, setDragActive] = useState(false)
    const [refreshCountdown, setRefreshCountdown] = useState<number | null>(null)

    // Helper to fetch latest status
    const fetchClaimStatus = async () => {
        if (!claimId) return
        try {
            const response = await axios.get(
                `${API_BASE_URL}/api/documents/status?claim_id=${claimId}`,
                { headers: { Authorization: `Bearer ${token}` } }
            )
            setDocuments(response.data)
        } catch (err) {
            console.error('Failed to load documents:', err)
        }
    }

    // Prevent double claim creation in React Strict Mode
    const claimCreationAttempted = useRef(false)

    // Redirect if not authenticated
    useEffect(() => {
        if (!isLoading && !user) {
            router.push('/login')
        }
    }, [user, isLoading, router])

    // 2. Modified Auto-create Effect - only creates if no claim ID exists
    useEffect(() => {
        // If we already have a claim ID from URL, don't create a new one!
        if (claimId) {
            console.log('📋 Resuming existing claim:', claimId)
            return
        }

        if (policyHolder && !claimCreationAttempted.current) {
            claimCreationAttempted.current = true
            createClaim()
        }
    }, [policyHolder, claimId])

    const createClaim = async () => {
        if (!policyHolder || !policyHolder.policy_holder_id) {
            console.error('Cannot create claim: policyHolder is null or missing ID')
            setError('Authentication error. Please log out and log in again.')
            return
        }

        try {
            console.log('Creating claim for policy holder:', policyHolder?.policy_holder_id)
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

            // 🔐 PERSIST CLAIM ID (Dual Strategy)
            setClaimId(newClaimId)

            // 1. Save to localStorage (survives refresh)
            localStorage.setItem('current_claim_id', newClaimId)

            // 2. Update URL (visible to user, shareable)
            const url = new URL(window.location.href)
            url.searchParams.set('claim_id', newClaimId)
            window.history.replaceState({}, '', url.toString())

            console.log('✅ Auto-created claim:', newClaimId)
        } catch (err: any) {
            console.error('Failed to create claim:', err)
            console.error('Error response:', err.response?.data)
            console.error('Error status:', err.response?.status)
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
            // Convert FileList to Array and add to selected files
            const newFiles = Array.from(e.target.files)
            setSelectedFiles(prev => [...prev, ...newFiles])
            setError('')
            console.log(`📁 ${newFiles.length} file(s) added to selection`)
        }
    }

    // Remove a file from selection
    const removeFile = (index: number) => {
        setSelectedFiles(prev => prev.filter((_, i) => i !== index))
    }

    // Batch upload function - uploads all selected files
    const uploadAllDocuments = async () => {
        if (selectedFiles.length === 0 || !claimId) {
            setError('Please select at least one file and ensure claim is created')
            return
        }

        setUploading(true)
        setError('')

        try {
            console.log(`📤 Starting batch upload of ${selectedFiles.length} file(s)...`)

            // Loop through each file and upload one by one
            for (let i = 0; i < selectedFiles.length; i++) {
                const file = selectedFiles[i]
                console.log(`\n📄 [${i + 1}/${selectedFiles.length}] Processing: ${file.name}`)

                try {
                    // Step 1: Get presigned URL
                    console.log('  � Step 1: Requesting presigned URL...')
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
                    console.log('  ✅ Presigned URL received:', file_id)

                    // Step 2: Upload to MinIO
                    console.log('  📤 Step 2: Uploading to MinIO...')
                    await axios.put(upload_url, file, {
                        headers: {
                            'Content-Type': file.type || 'application/octet-stream'
                        }
                    })
                    console.log('  ✅ File uploaded to MinIO')

                    // Step 3: Trigger processing
                    console.log('  ⚙️ Step 3: Triggering processing...')
                    await axios.post(
                        `${API_BASE_URL}/api/documents/${file_id}/process`,
                        {},
                        {
                            headers: { Authorization: `Bearer ${token}` }
                        }
                    )
                    console.log('  ✅ Processing triggered')

                } catch (fileErr: any) {
                    console.error(`  ❌ Failed to upload ${file.name}:`, fileErr)
                    // Continue with next file even if one fails
                }
            }

            console.log('\n✅ Batch upload complete!')

            // Start global polling for all documents
            setProcessing(true)
            fetchClaimStatus()

            // Start 6-second countdown for refresh button
            setRefreshCountdown(6)

            // Clear selected files
            setSelectedFiles([])
            setDocumentType('auto')

        } catch (err: any) {
            console.error('Batch upload error:', err)
            setError(err.response?.data?.detail || err.message || 'Batch upload failed')
        } finally {
            setUploading(false)
        }
    }



    // Real-time updates via SSE
    useEffect(() => {
        if (!claimId || !token) return;

        // 1. Initial Load
        fetchClaimStatus();

        // 2. Setup Real-time Listener
        console.log(`🔌 Connecting to SSE stream for claim ${claimId}...`);
        const eventSource = new EventSource(`${API_BASE_URL}/api/claims/${claimId}/stream`);

        eventSource.onopen = () => {
            console.log("🟢 SSE Connection Opened");
        };

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log("📨 Received SSE update:", data);

                if (data.type === 'document_update') {
                    setDocuments(prev => {
                        // Check if document already exists
                        const existingIndex = prev.findIndex(doc => doc.file_id === data.file_id);

                        if (existingIndex >= 0) {
                            // Update existing document
                            return prev.map(doc =>
                                doc.file_id === data.file_id
                                    ? { ...doc, status: data.status, extracted_data: data.extracted_data }
                                    : doc
                            );
                        } else {
                            // Add new document (handles race condition where SSE arrives before fetchClaimStatus)
                            console.log("📄 Adding new document from SSE:", data.file_id);
                            return [...prev, {
                                file_id: data.file_id,
                                filename: data.filename || "Unknown",
                                document_type: data.document_type || "auto",
                                status: data.status,
                                extracted_data: data.extracted_data
                            }];
                        }
                    });

                    // If processed, stop the "Processing..." spinner implies logic? 
                    // We can check if any are still processing
                    if (data.status === 'processed' || data.status === 'failed') {
                        setProcessing(prev => {
                            // This might be tricky with stale state, but UI updates based on documents list
                            return prev;
                        });
                    }
                }

                if (data.type === 'claim_decision') {
                    console.log("✅ Claim adjudicated:", data.decision);
                }
            } catch (e) {
                console.error("Error parsing SSE data:", e);
            }
        };

        eventSource.onerror = (err) => {
            console.error("🔴 SSE Error:", err);
            // EventSource automatically retries
        };

        return () => {
            console.log("🔌 Closing SSE connection");
            eventSource.close();
        };
    }, [claimId, token]);

    // Countdown timer for refresh button
    useEffect(() => {
        if (refreshCountdown === null || refreshCountdown <= 0) return;

        const timer = setTimeout(() => {
            setRefreshCountdown(prev => {
                if (prev === null || prev <= 1) {
                    return 0; // Enable button
                }
                return prev - 1;
            });
        }, 1000);

        return () => clearTimeout(timer);
    }, [refreshCountdown]);

    // Load existing documents for claim
    useEffect(() => {
        if (claimId && token) {
            loadDocuments()
        }
    }, [claimId, token])

    const loadDocuments = async () => {
        try {
            const response = await axios.get(
                `${API_BASE_URL}/api/documents/status?claim_id=${claimId}`,
                {
                    headers: { Authorization: `Bearer ${token}` }
                }
            )
            setDocuments(response.data)
        } catch (err) {
            console.error('Failed to load documents:', err)
        }
    }

    // Live polling hook - automatically updates document status
    useEffect(() => {
        let intervalId: NodeJS.Timeout

        const fetchUpdates = async () => {
            if (!claimId || !token) return

            try {
                // Fetch the latest status for ALL documents
                const response = await axios.get(
                    `${API_BASE_URL}/api/documents/status?claim_id=${claimId}`,
                    { headers: { Authorization: `Bearer ${token}` } }
                )

                setDocuments(response.data)

                // Intelligence: Only keep polling if something is still processing
                const hasPending = response.data.some((doc: UploadedDocument) =>
                    doc.status === 'processing' || doc.status === 'uploaded'
                )

                if (!hasPending) {
                    clearInterval(intervalId) // Stop wasting resources if everything is done
                    setProcessing(false)
                }
            } catch (err) {
                console.error('Polling error:', err)
            }
        }

        // Start polling if we have an active Claim ID
        if (claimId) {
            fetchUpdates() // Initial fetch
            intervalId = setInterval(fetchUpdates, 3000) // Poll every 3 seconds
        }

        return () => clearInterval(intervalId) // Cleanup on unmount
    }, [claimId, token]) // Re-run if claimId changes


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

                {/* Upload Section */}
                <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
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
                        {uploading ? '📤 Uploading...' : processing ? '⚙️ Processing...' : `📤 Upload ${selectedFiles.length} File(s)`}
                    </button>
                    {/* Auto-Refresh Button (activates after 6 seconds) */}
                    {refreshCountdown !== null && (
                        <button
                            onClick={() => {
                                console.log('🔄 Manual refresh triggered');
                                fetchClaimStatus();
                                setRefreshCountdown(null);
                            }}
                            disabled={refreshCountdown > 0}
                            className={`w-full mt-3 py-3 px-6 rounded-lg font-semibold transition-all border ${
                                refreshCountdown > 0
                                    ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
                                    : 'bg-green-50 text-green-700 border-green-300 hover:bg-green-100 cursor-pointer'
                            }`}
                        >
                            {refreshCountdown > 0 
                                ? `⏳ Refresh available in ${refreshCountdown}s...` 
                                : '🔄 Refresh Status Now'}
                        </button>
                    )}
                    {/* Error Message */}
                    {error && (
                        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                            <p className="text-red-800 text-sm">❌ {error}</p>
                        </div>
                    )}
                </div>

                {/* Documents List */}
                {documents.length > 0 && (
                    <div className="bg-white rounded-2xl shadow-xl p-8">
                        <h2 className="text-2xl font-bold mb-6">Uploaded Documents</h2>
                        <div className="space-y-4">
                            {documents.map((doc) => {
                                // Helper function to map backend status to UI display
                                const getStatusDisplay = (status: string) => {
                                    switch (status) {
                                        case 'uploaded':
                                            return { text: 'Queued', icon: '⏳', color: 'text-gray-500' };
                                        case 'processing':
                                            return { text: 'Extracting Information...', icon: '⚙️', color: 'text-blue-600 animate-pulse' };
                                        case 'processed':
                                            return { text: 'Done', icon: '✅', color: 'text-green-600' };
                                        case 'failed':
                                            return { text: 'Failed', icon: '❌', color: 'text-red-600' };
                                        default:
                                            return { text: 'Waiting...', icon: '🕒', color: 'text-gray-400' };
                                    }
                                };

                                const statusInfo = getStatusDisplay(doc.status);

                                return (
                                    <div
                                        key={doc.file_id}
                                        className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
                                    >
                                        <div className="flex justify-between items-start mb-4">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-3 mb-2">
                                                    {/* File Name */}
                                                    <h3 className="font-semibold text-lg text-gray-900">
                                                        {doc.filename}
                                                    </h3>

                                                    {/* Dynamic Status with Icon and Animation */}
                                                    <span className={`text-sm flex items-center gap-2 ${statusInfo.color}`}>
                                                        <span>{statusInfo.icon}</span>
                                                        <span className="font-medium">{statusInfo.text}</span>
                                                    </span>
                                                </div>

                                                <p className="text-sm text-gray-500">
                                                    Type: <span className="font-medium">{doc.document_type}</span>
                                                </p>
                                            </div>

                                            {/* Checkmark appears ONLY when processed */}
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
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
