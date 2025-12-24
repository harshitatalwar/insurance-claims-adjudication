'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '../../../../contexts/AuthContext'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { ArrowLeft, CheckCircle, XCircle, AlertCircle, Banknote, FileText, ArrowRight, Home, Upload, Shield } from 'lucide-react'

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

    const [claimId, setClaimId] = useState<string | null>(null)
    const [claimData, setClaimData] = useState<ClaimData | null>(null)
    const [loading, setLoading] = useState(true)

    // Initial Load
    useEffect(() => {
        if (!isLoading && !user) router.push('/login')
        if (typeof window !== 'undefined') {
            const urlClaimId = new URLSearchParams(window.location.search).get('claim_id')
            if (urlClaimId) setClaimId(urlClaimId)
            else setTimeout(() => router.push('/upload/step1'), 100)
        }
    }, [user, isLoading, router])

    // Fetch Logic
    useEffect(() => {
        if (claimId && token) fetchClaimData()
    }, [claimId, token])

    // SSE Logic
    useEffect(() => {
        if (!claimId || !token) return
        const eventSource = new EventSource(`${API_BASE_URL}/api/claims/${claimId}/stream`)
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                if (data.type === 'claim_decision') fetchClaimData()
            } catch (e) {
                console.error("SSE Error", e)
            }
        }
        return () => eventSource.close()
    }, [claimId, token])

    const fetchClaimData = async () => {
        try {
            const res = await axios.get(`${API_BASE_URL}/api/claims/${claimId}`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            setClaimData(res.data)
        } catch (err) {
            console.error("Fetch Error", err)
        } finally {
            setLoading(false)
        }
    }

    if (isLoading || loading) return (
        <div className="min-h-screen flex items-center justify-center bg-slate-900">
            <div className="animate-pulse flex flex-col items-center gap-4">
                <Shield className="w-12 h-12 text-brand-500 animate-bounce" />
                <p className="text-brand-200 text-lg font-medium">Retrieving Adjudication Record...</p>
            </div>
        </div>
    )

    if (!user) return null

    const hasDecision = claimData && (claimData.decision || ['approved', 'rejected', 'under_review'].includes(claimData.status))
    const isApproved = claimData?.decision === 'APPROVED' || claimData?.status === 'approved'
    const isRejected = claimData?.decision === 'REJECTED' || claimData?.status === 'rejected'
    const isPartial = claimData?.decision === 'PARTIAL'

    return (
        <div className="min-h-screen px-4 py-8 relative flex flex-col items-center">

            <div className="w-full max-w-4xl relative z-10 animate-fade-in">
                {/* Header Nav */}
                <button
                    onClick={() => router.push(`/upload/step2?claim_id=${claimId}`)}
                    className="flex items-center gap-2 text-slate-400 hover:text-white mb-8 transition-colors"
                >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Back to Documents</span>
                </button>

                {hasDecision ? (
                    <div className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 overflow-hidden">

                        {/* 1. Status Banner */}
                        <div className={`
                            relative overflow-hidden p-8 text-center border-b
                            ${isApproved ? 'bg-emerald-50/80 border-emerald-100' : ''}
                            ${isRejected ? 'bg-red-50/80 border-red-100' : ''}
                            ${(!isApproved && !isRejected) ? 'bg-amber-50/80 border-amber-100' : ''}
                        `}>
                            <div className="flex flex-col items-center relative z-10">
                                {isApproved && <div className="p-4 bg-emerald-100 rounded-full mb-4 text-emerald-600"><CheckCircle className="w-12 h-12" /></div>}
                                {isRejected && <div className="p-4 bg-red-100 rounded-full mb-4 text-red-600"><XCircle className="w-12 h-12" /></div>}
                                {!(isApproved || isRejected) && <div className="p-4 bg-amber-100 rounded-full mb-4 text-amber-600"><AlertCircle className="w-12 h-12" /></div>}

                                <h1 className={`text-3xl font-bold tracking-tight mb-2
                                    ${isApproved ? 'text-emerald-900' : ''}
                                    ${isRejected ? 'text-red-900' : ''}
                                    ${(!isApproved && !isRejected) ? 'text-amber-900' : ''}
                                `}>
                                    {claimData?.decision?.replace('_', ' ') || claimData?.status?.toUpperCase().replace('_', ' ')}
                                </h1>
                                <p className="text-slate-500 font-medium">
                                    Adjudication Completed on {new Date(claimData?.processed_at || Date.now()).toLocaleDateString()}
                                </p>
                            </div>
                        </div>

                        {/* 2. Financial Breakdown (If Approved/Partial) */}
                        {(isApproved || isPartial) && (
                            <div className="grid grid-cols-2 divide-x divide-slate-100 border-b border-slate-100">
                                <div className="p-8 text-center group hover:bg-slate-50 transition-colors">
                                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Total Claimed</p>
                                    <p className="text-3xl font-bold text-slate-700">₹{claimData.claimed_amount?.toFixed(2) || '0.00'}</p>
                                </div>
                                <div className="p-8 text-center bg-emerald-50/30 group hover:bg-emerald-50/50 transition-colors">
                                    <p className="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-2 flex justify-center items-center gap-1">
                                        <Banknote className="w-3 h-3" /> Approved Amount
                                    </p>
                                    <p className="text-4xl font-bold text-emerald-600">₹{claimData.approved_amount?.toFixed(2) || '0.00'}</p>
                                </div>
                            </div>
                        )}

                        {/* 3. Details Grid */}
                        <div className="p-8 grid md:grid-cols-2 gap-8">

                            {/* Notes Section */}
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 text-slate-800 font-semibold border-b border-slate-100 pb-2">
                                    <FileText className="w-4 h-4 text-brand-500" />
                                    <h3>Adjudicator Notes</h3>
                                </div>
                                <p className="text-slate-600 text-sm leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-100">
                                    {claimData?.notes || "No additional notes provided."}
                                </p>

                                {claimData?.rejection_reasons && claimData.rejection_reasons.length > 0 && (
                                    <div className="mt-4">
                                        <h4 className="text-xs font-bold text-red-600 uppercase tracking-wider mb-2">Rejection Factors</h4>
                                        <ul className="space-y-2">
                                            {claimData.rejection_reasons.map((r, i) => (
                                                <li key={i} className="flex gap-2 text-sm text-red-700 bg-red-50 p-2 rounded border border-red-100">
                                                    <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
                                                    {r}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>

                            {/* Next Steps */}
                            <div className="bg-brand-50/50 rounded-xl p-6 border border-brand-100">
                                <div className="flex items-center gap-2 text-brand-900 font-semibold mb-4">
                                    <ArrowRight className="w-4 h-4" />
                                    <h3>Recommended Next Steps</h3>
                                </div>
                                <div className="flex gap-4">
                                    <div className="w-1 bg-brand-200 rounded-full"></div>
                                    <p className="text-brand-800 text-sm leading-relaxed">
                                        {claimData?.next_steps || "Please verify the approved amount with the finance department."}
                                    </p>
                                </div>

                                <div className="mt-6 pt-6 border-t border-brand-200/50 flex flex-col gap-3">
                                    <button
                                        onClick={() => {
                                            localStorage.removeItem('current_claim_id')
                                            router.push('/upload/step1')
                                        }}
                                        className="w-full py-2.5 bg-white border border-brand-200 text-brand-700 rounded-lg text-sm font-semibold hover:bg-brand-50 hover:border-brand-300 transition-all flex justify-center items-center gap-2 shadow-sm"
                                    >
                                        <Upload className="w-4 h-4" /> Process Another Claim
                                    </button>
                                    <button
                                        onClick={() => router.push('/dashboard')}
                                        className="w-full py-2.5 bg-brand-600 text-white rounded-lg text-sm font-semibold hover:bg-brand-700 transition-all flex justify-center items-center gap-2 shadow-md hover:shadow-lg hover:-translate-y-0.5"
                                    >
                                        <Home className="w-4 h-4" /> Return to Dashboard
                                    </button>
                                </div>
                            </div>

                        </div>

                        {/* Footer Meta */}
                        <div className="bg-slate-50 border-t border-slate-100 p-4 text-center text-xs text-slate-400 font-mono">
                            Claim Reference: {claimId} • Confidence Score: {(claimData?.confidence_score || 0) * 100}%
                        </div>

                    </div>
                ) : (
                    /* Loading Skeletons for Decision */
                    <div className="bg-white/10 backdrop-blur-md rounded-2xl p-12 text-center border border-white/10 animate-pulse">
                        <div className="w-20 h-20 bg-white/20 rounded-full mx-auto mb-6"></div>
                        <div className="h-4 bg-white/20 rounded-full max-w-sm mx-auto mb-4"></div>
                        <div className="h-3 bg-white/10 rounded-full max-w-xs mx-auto"></div>
                    </div>
                )}
            </div>
        </div>
    )
}
