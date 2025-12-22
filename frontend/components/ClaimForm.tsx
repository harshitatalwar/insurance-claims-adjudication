'use client'

import { useState, useEffect } from 'react'
import { User, Calendar, DollarSign, FileText, CheckCircle, XCircle, Clock, Loader } from 'lucide-react'
import DocumentChecklist from './DocumentChecklist'
import FileUpload from './FileUpload'
import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

interface PolicyHolder {
    policy_holder_id: string
    policy_holder_name: string
    email: string
    phone: string
    annual_limit: number
    annual_limit_used: number
    date_of_birth: string
}

interface Document {
    document_id: string
    document_type: string
    file_path: string
    ocr_text: string | null
    extracted_data: any
    created_at: string
}

interface AdjudicationResult {
    decision: string
    approved_amount: number
    eligible_amount: number
    co_payment_amount: number
    confidence_score: number
    rejection_reasons: string[]
    notes: string
    next_steps: string
}

export default function ClaimForm() {
    const [policyHolders, setPolicyHolders] = useState<PolicyHolder[]>([])
    const [selectedPolicyHolder, setSelectedPolicyHolder] = useState<PolicyHolder | null>(null)
    const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
    const [documents, setDocuments] = useState<Document[]>([])
    const [claimId, setClaimId] = useState<string | null>(null)
    const [adjudicationResult, setAdjudicationResult] = useState<AdjudicationResult | null>(null)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [submitStatus, setSubmitStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null)
    const [isPolling, setIsPolling] = useState(false)

    // Fetch policy holders on mount
    useEffect(() => {
        fetchPolicyHolders()
    }, [])

    // Poll for document status when claim is created
    useEffect(() => {
        if (claimId && isPolling) {
            const interval = setInterval(() => {
                fetchDocumentStatus()
            }, 3000) // Poll every 3 seconds

            return () => clearInterval(interval)
        }
    }, [claimId, isPolling])

    // Poll for adjudication result
    useEffect(() => {
        if (claimId && isPolling && documents.length > 0) {
            const allProcessed = documents.every(doc => doc.ocr_text !== null)
            if (allProcessed) {
                const interval = setInterval(() => {
                    fetchAdjudicationResult()
                }, 2000) // Poll every 2 seconds

                return () => clearInterval(interval)
            }
        }
    }, [claimId, isPolling, documents])

    const fetchPolicyHolders = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/policy-holders/`)
            setPolicyHolders(response.data)
            // Auto-select first policy holder if available
            if (response.data.length > 0) {
                setSelectedPolicyHolder(response.data[0])
            }
        } catch (error) {
            console.error('Failed to fetch policy holders:', error)
        }
    }

    const fetchDocumentStatus = async () => {
        if (!claimId) return
        try {
            const response = await axios.get(`${API_BASE_URL}/api/documents/${claimId}`)
            setDocuments(response.data)
        } catch (error) {
            console.error('Failed to fetch document status:', error)
        }
    }

    const fetchAdjudicationResult = async () => {
        if (!claimId) return
        try {
            const response = await axios.get(`${API_BASE_URL}/api/adjudication/claims/${claimId}/decision`)
            setAdjudicationResult(response.data)
            setIsPolling(false) // Stop polling once we have the result
        } catch (error) {
            // Decision might not be ready yet, keep polling
            console.log('Adjudication not ready yet...')
        }
    }

    const handlePolicyHolderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const holder = policyHolders.find(ph => ph.policy_holder_id === e.target.value)
        setSelectedPolicyHolder(holder || null)
    }

    const handleSubmit = async () => {
        if (!selectedPolicyHolder) {
            setSubmitStatus({ type: 'error', message: 'Please select a policy holder' })
            return
        }

        if (uploadedFiles.length === 0) {
            setSubmitStatus({ type: 'error', message: 'Please upload at least one document' })
            return
        }

        setIsSubmitting(true)
        setSubmitStatus(null)

        try {
            // 1. Create the claim
            const claimResponse = await axios.post(`${API_BASE_URL}/api/claims/`, {
                policy_holder_id: selectedPolicyHolder.policy_holder_id,
                treatment_type: 'consultation',
                claimed_amount: 5000, // Default amount, can be made dynamic
                treatment_date: new Date().toISOString().split('T')[0],
                provider_name: 'City Hospital',
                provider_network: true,
                doctor_name: 'Dr. Smith',
                diagnosis: 'General Consultation'
            })

            const newClaimId = claimResponse.data.claim_id
            setClaimId(newClaimId)

            // 2. Upload documents
            for (const file of uploadedFiles) {
                const formData = new FormData()
                formData.append('file', file)

                let documentType = 'other'
                const fileName = file.name.toLowerCase()
                if (fileName.includes('prescription') || fileName.includes('rx')) {
                    documentType = 'prescription'
                } else if (fileName.includes('bill') || fileName.includes('invoice') || fileName.includes('receipt')) {
                    documentType = 'bill'
                } else if (fileName.includes('report') || fileName.includes('lab') || fileName.includes('test')) {
                    documentType = 'report'
                }

                await axios.post(
                    `${API_BASE_URL}/api/documents/${newClaimId}/upload?document_type=${documentType}`,
                    formData,
                    {
                        headers: {
                            'Content-Type': 'multipart/form-data',
                        },
                    }
                )
            }

            // 3. Start polling for status
            setIsPolling(true)

            // 4. Trigger adjudication
            setTimeout(async () => {
                try {
                    await axios.post(`${API_BASE_URL}/api/adjudication/claims/${newClaimId}/adjudicate`)
                } catch (error) {
                    console.error('Adjudication trigger failed:', error)
                }
            }, 5000) // Wait 5 seconds for OCR to process

            setSubmitStatus({
                type: 'success',
                message: `Claim ${newClaimId} submitted successfully! Processing documents...`
            })

        } catch (error: any) {
            console.error('Failed to submit claim:', error)
            setSubmitStatus({
                type: 'error',
                message: error.response?.data?.detail || 'Failed to submit claim. Please try again.'
            })
        } finally {
            setIsSubmitting(false)
        }
    }

    const getDocumentStatusIcon = (doc: Document) => {
        if (doc.ocr_text === null) {
            return <Loader className="w-5 h-5 text-blue-500 animate-spin" />
        } else if (doc.extracted_data && Object.keys(doc.extracted_data).length > 0) {
            return <CheckCircle className="w-5 h-5 text-green-500" />
        } else {
            return <XCircle className="w-5 h-5 text-red-500" />
        }
    }

    const getDecisionBadge = (decision: string) => {
        const baseClasses = "inline-flex items-center px-3 py-1 rounded-full text-sm font-medium"
        switch (decision) {
            case 'APPROVED':
                return `${baseClasses} bg-green-100 text-green-800`
            case 'REJECTED':
                return `${baseClasses} bg-red-100 text-red-800`
            case 'PARTIAL':
                return `${baseClasses} bg-yellow-100 text-yellow-800`
            case 'MANUAL_REVIEW':
                return `${baseClasses} bg-blue-100 text-blue-800`
            default:
                return `${baseClasses} bg-gray-100 text-gray-800`
        }
    }

    return (
        <div className="max-w-6xl mx-auto px-4 py-8">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                {/* Left Column - Policy Holder Details (Read-only) */}
                <div className="lg:col-span-1">
                    <div className="insurance-card">
                        {/* Policy Holder Selector */}
                        <div className="mb-6">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Select Policy Holder
                            </label>
                            <select
                                className="insurance-input w-full"
                                value={selectedPolicyHolder?.policy_holder_id || ''}
                                onChange={handlePolicyHolderChange}
                            >
                                <option value="">-- Select Policy Holder --</option>
                                {policyHolders.map(ph => (
                                    <option key={ph.policy_holder_id} value={ph.policy_holder_id}>
                                        {ph.policy_holder_name} ({ph.policy_holder_id})
                                    </option>
                                ))}
                            </select>
                        </div>

                        {selectedPolicyHolder && (
                            <>
                                {/* Policy Holder Avatar */}
                                <div className="flex items-center space-x-4 mb-6">
                                    <div className="w-16 h-16 bg-insurance-blue rounded-full flex items-center justify-center">
                                        <User className="w-8 h-8 text-white" />
                                    </div>
                                    <div>
                                        <h2 className="text-lg font-semibold text-gray-900">Policy Holder Details</h2>
                                        <p className="text-sm text-gray-500">Read-only information</p>
                                    </div>
                                </div>

                                {/* Read-only Details */}
                                <div className="space-y-4">
                                    <div className="p-3 bg-gray-50 rounded-md">
                                        <p className="text-xs text-gray-500">Policy Holder ID</p>
                                        <p className="text-sm font-medium text-gray-900">{selectedPolicyHolder.policy_holder_id}</p>
                                    </div>

                                    <div className="p-3 bg-gray-50 rounded-md">
                                        <p className="text-xs text-gray-500">Name</p>
                                        <p className="text-sm font-medium text-gray-900">{selectedPolicyHolder.policy_holder_name}</p>
                                    </div>

                                    <div className="p-3 bg-gray-50 rounded-md">
                                        <p className="text-xs text-gray-500">Email</p>
                                        <p className="text-sm font-medium text-gray-900">{selectedPolicyHolder.email}</p>
                                    </div>

                                    <div className="p-3 bg-gray-50 rounded-md">
                                        <p className="text-xs text-gray-500">Phone</p>
                                        <p className="text-sm font-medium text-gray-900">{selectedPolicyHolder.phone}</p>
                                    </div>

                                    <div className="p-3 bg-gray-50 rounded-md">
                                        <p className="text-xs text-gray-500">Date of Birth</p>
                                        <p className="text-sm font-medium text-gray-900">
                                            {new Date(selectedPolicyHolder.date_of_birth).toLocaleDateString()}
                                        </p>
                                    </div>

                                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
                                        <p className="text-xs text-blue-600">Annual Limit</p>
                                        <p className="text-lg font-bold text-blue-900">
                                            ₹{selectedPolicyHolder.annual_limit.toLocaleString()}
                                        </p>
                                        <div className="mt-2">
                                            <div className="flex justify-between text-xs text-blue-700 mb-1">
                                                <span>Used: ₹{selectedPolicyHolder.annual_limit_used.toLocaleString()}</span>
                                                <span>
                                                    {((selectedPolicyHolder.annual_limit_used / selectedPolicyHolder.annual_limit) * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                            <div className="w-full bg-blue-200 rounded-full h-2">
                                                <div
                                                    className="bg-blue-600 h-2 rounded-full"
                                                    style={{
                                                        width: `${Math.min((selectedPolicyHolder.annual_limit_used / selectedPolicyHolder.annual_limit) * 100, 100)}%`
                                                    }}
                                                ></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Important Note */}
                                <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                                    <div className="flex items-start space-x-2">
                                        <FileText className="w-5 h-5 text-yellow-600 mt-0.5" />
                                        <div>
                                            <p className="text-sm font-medium text-yellow-800">Important Note</p>
                                            <p className="text-sm text-yellow-700 mt-1">
                                                Policy holder details are fetched from the database and cannot be edited here.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* Right Column - Document Upload and Status */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Dynamic Document Status */}
                    {documents.length > 0 && (
                        <div className="insurance-card">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">Uploaded Documents</h3>
                            <div className="space-y-3">
                                {documents.map((doc) => (
                                    <div key={doc.document_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                        <div className="flex items-center space-x-3">
                                            {getDocumentStatusIcon(doc)}
                                            <div>
                                                <p className="text-sm font-medium text-gray-900">
                                                    {doc.file_path.split('/').pop()}
                                                </p>
                                                <p className="text-xs text-gray-500">
                                                    Type: {doc.document_type} • ID: {doc.document_id}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            {doc.ocr_text === null ? (
                                                <span className="text-xs text-blue-600">Processing OCR...</span>
                                            ) : doc.extracted_data && Object.keys(doc.extracted_data).length > 0 ? (
                                                <span className="text-xs text-green-600">✓ Extracted</span>
                                            ) : (
                                                <span className="text-xs text-red-600">✗ Failed</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Adjudication Results */}
                    {adjudicationResult && (
                        <div className="insurance-card">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">Adjudication Result</h3>

                            <div className="mb-4">
                                <span className={getDecisionBadge(adjudicationResult.decision)}>
                                    {adjudicationResult.decision}
                                </span>
                            </div>

                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div className="p-3 bg-gray-50 rounded-md">
                                    <p className="text-xs text-gray-500">Approved Amount</p>
                                    <p className="text-lg font-bold text-green-600">
                                        ₹{adjudicationResult.approved_amount.toLocaleString()}
                                    </p>
                                </div>
                                <div className="p-3 bg-gray-50 rounded-md">
                                    <p className="text-xs text-gray-500">Confidence Score</p>
                                    <p className="text-lg font-bold text-blue-600">
                                        {(adjudicationResult.confidence_score * 100).toFixed(0)}%
                                    </p>
                                </div>
                            </div>

                            {adjudicationResult.rejection_reasons.length > 0 && (
                                <div className="p-4 bg-red-50 border border-red-200 rounded-md mb-4">
                                    <p className="text-sm font-medium text-red-800 mb-2">Rejection Reasons:</p>
                                    <ul className="text-sm text-red-700 space-y-1">
                                        {adjudicationResult.rejection_reasons.map((reason, idx) => (
                                            <li key={idx}>• {reason}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {adjudicationResult.notes && (
                                <div className="p-4 bg-blue-50 border border-blue-200 rounded-md mb-4">
                                    <p className="text-sm font-medium text-blue-800 mb-1">Notes:</p>
                                    <p className="text-sm text-blue-700">{adjudicationResult.notes}</p>
                                </div>
                            )}

                            {adjudicationResult.next_steps && (
                                <div className="p-4 bg-green-50 border border-green-200 rounded-md">
                                    <p className="text-sm font-medium text-green-800 mb-1">Next Steps:</p>
                                    <p className="text-sm text-green-700">{adjudicationResult.next_steps}</p>
                                </div>
                            )}
                        </div>
                    )}

                    <DocumentChecklist />
                    <FileUpload
                        uploadedFiles={uploadedFiles}
                        setUploadedFiles={setUploadedFiles}
                    />

                    {/* Status Messages */}
                    {submitStatus && (
                        <div className={`p-4 rounded-md ${submitStatus.type === 'success'
                            ? 'bg-green-50 border border-green-200'
                            : 'bg-red-50 border border-red-200'
                            }`}>
                            <p className={`text-sm ${submitStatus.type === 'success' ? 'text-green-800' : 'text-red-800'
                                }`}>
                                {submitStatus.message}
                            </p>
                        </div>
                    )}

                    {/* Submit Button */}
                    <div className="flex justify-end">
                        <button
                            onClick={handleSubmit}
                            className="insurance-button px-8 py-3 text-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                            disabled={isSubmitting || !selectedPolicyHolder || uploadedFiles.length === 0}
                        >
                            {isSubmitting ? 'Submitting...' : 'Submit Claim for Review'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
