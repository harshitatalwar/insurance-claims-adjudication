'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function UploadRedirectPage() {
    const router = useRouter()

    useEffect(() => {
        console.log('📍 Upload page - redirecting to step1')
        // Use window.location to get query params client-side only
        const params = new URLSearchParams(window.location.search)
        const claimId = params.get('claim_id')

        // Redirect to step1 with claim_id if present
        if (claimId) {
            console.log('📍 Redirecting with claim_id:', claimId)
            router.push(`/upload/step1?claim_id=${claimId}`)
        } else {
            console.log('📍 Redirecting to step1')
            router.push('/upload/step1')
        }
    }, [router])

    return (
        <div className="min-h-screen flex items-center justify-center">
            <div className="text-xl">Redirecting...</div>
        </div>
    )
}
