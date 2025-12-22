'use client'

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

export default function UploadRedirectPage() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const claimId = searchParams.get('claim_id')

    useEffect(() => {
        // Redirect to step1 with claim_id if present
        if (claimId) {
            router.push(`/upload/step1?claim_id=${claimId}`)
        } else {
            router.push('/upload/step1')
        }
    }, [claimId, router])

    return (
        <div className="min-h-screen flex items-center justify-center">
            <div className="text-xl">Redirecting...</div>
        </div>
    )
}
