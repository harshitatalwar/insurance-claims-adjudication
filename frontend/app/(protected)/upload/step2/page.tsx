'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '../../../../contexts/AuthContext'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { ArrowLeft, Loader2, ShieldCheck, Sparkles } from 'lucide-react'
import DocumentCard from '../../../../components/ui/DocumentCard'

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

    const [claimId, setClaimId] = useState<string | null>(null)
    const [documents, setDocuments] = useState<UploadedDocument[]>([])
    const [loading, setLoading] = useState(true)
    const [adjudicating, setAdjudicating] = useState(false)

    // Initial Load & Auth Check
    useEffect(() => {
        if (!isLoading && !user) router.push('/login')

        if (typeof window !== 'undefined') {
            const urlClaimId = new URLSearchParams(window.location.search).get('claim_id')
            if (urlClaimId) {
                setClaimId(urlClaimId)
            } else {
                // small delay to prevent flash if query param is slow to read
                setTimeout(() => router.push('/upload/step1'), 100)
            }
        }
    }, [user, isLoading, router])

    // Load Data
    useEffect(() => {
        if (claimId && token) fetchDocuments()
    }, [claimId, token])

    // SSE Stream for Real-time Updates
    useEffect(() => {
        if (!claimId || !token) return

        const eventSource = new EventSource(`${API_BASE_URL}/api/claims/${claimId}/stream`)

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)

                if (data.type === 'document_update') {
                    setDocuments(prev => {
                        const exists = prev.find(d => d.file_id === data.file_id)
                        if (exists) {
                            return prev.map(d => d.file_id === data.file_id ? { ...d, ...data } : d)
                        } else {
                            return [...prev, {
                                file_id: data.file_id,
                                filename: data.filename || "Unknown Doc",
                                document_type: data.document_type || "document",
                                status: data.status,
                                extracted_data: data.extracted_data
                            }]
                        }
                    })
                }

                if (data.type === 'claim_decision') {
                    router.push(`/upload/step3?claim_id=${claimId}`)
                }
            } catch (e) {
                console.error("SSE Parse Error", e)
            }
        }

        return () => eventSource.close()
    }, [claimId, token, router])

    // Monitor completion for fallback and UI state
    useEffect(() => {
        if (documents.length > 0 && documents.every(d => d.status === 'processed' || d.status === 'failed')) {
            setAdjudicating(true)
            // Safety fallback
            const timer = setTimeout(() => router.push(`/upload/step3?claim_id=${claimId}`), 8000)
            return () => clearTimeout(timer)
        }
    }, [documents, claimId])

    const fetchDocuments = async () => {
        try {
            const res = await axios.get(`${API_BASE_URL}/api/documents/status?claim_id=${claimId}`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            setDocuments(res.data)
        } catch (err) {
            console.error("Fetch error", err)
        } finally {
            setLoading(false)
        }
    }

    if (isLoading || loading) return (
        <div className="min-h-screen flex items-center justify-center bg-slate-900">
            <Loader2 className="w-10 h-10 text-brand-500 animate-spin" />
        </div>
    )

    if (!user) return null

    return (
        <div className="min-h-screen px-4 py-8 relative">
            {/* Background elements handled by global CSS, just container here */}
            <div className="max-w-6xl mx-auto">

                {/* Header Section */}
                <div className="flex flex-col md:flex-row justify-between items-center mb-10 gap-4 animate-fade-in">
                    <button
                        onClick={() => router.push(`/upload/step1?claim_id=${claimId}`)}
                        className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors self-start md:self-auto"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        <span>Back</span>
                    </button>

                    <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/10 backdrop-blur-md border border-white/10 text-brand-100 text-sm">
                        <ShieldCheck className="w-4 h-4" />
                        <span className="font-mono opacity-80">CLAIM ID: {claimId}</span>
                    </div>
                </div>

                {/* Main Status Display */}
                <div className="text-center mb-12 animate-slide-up">
                    <h1 className="text-3xl md:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white via-indigo-100 to-indigo-200 mb-4">
                        {adjudicating ? 'Finalizing Analysis...' : 'Processing Documents'}
                    </h1>
                    <p className="text-indigo-200/70 text-lg max-w-2xl mx-auto">
                        {adjudicating
                            ? "Our AI is cross-referencing extracted data with your policy terms to adjudicate this claim."
                            : "We're extracting key information from your uploaded files. This typically takes 10-20 seconds."
                        }
                    </p>
                </div>

                {/* Adjudication Overlay/Spinner */}
                {adjudicating && (
                    <div className="mb-12 flex justify-center animate-pulse-slow">
                        <div className="flex items-center gap-3 px-6 py-3 bg-emerald-500/10 border border-emerald-500/20 rounded-full backdrop-blur-md text-emerald-300">
                            <Sparkles className="w-5 h-5 animate-pulse" />
                            <span className="font-semibold"> AI Adjudication in Progress</span>
                        </div>
                    </div>
                )}

                {/* Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {documents.map((doc, idx) => (
                        <div key={doc.file_id} className="animate-slide-up" style={{ animationDelay: `${idx * 100}ms` }}>
                            <DocumentCard
                                filename={doc.filename}
                                type={doc.document_type}
                                status={doc.status}
                                extractedData={doc.extracted_data}
                                confidence={doc.confidence_score}
                            />
                        </div>
                    ))}

                    {/* Add Document Placeholder */}
                    {!adjudicating && (
                        <div
                            onClick={() => router.push(`/upload/step1?claim_id=${claimId}`)}
                            className="group h-full min-h-[240px] border-2 border-dashed border-white/10 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-brand-500/50 hover:bg-brand-500/5 transition-all duration-300"
                        >
                            <div className="p-4 rounded-full bg-white/5 group-hover:bg-brand-500/20 transition-colors mb-4">
                                <span className="text-2xl">+</span>
                            </div>
                            <p className="text-slate-400 group-hover:text-brand-300 font-medium">Upload More</p>
                        </div>
                    )}
                </div>

            </div>
        </div>
    )
}
