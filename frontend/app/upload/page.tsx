'use client'

import { useEffect } from 'react'

export default function UploadRedirectPage() {
    useEffect(() => {
        // Use window.location to get query params client-side only
        const params = new URLSearchParams(window.location.search)
        const claimId = params.get('claim_id')

        // Redirect to step1 with claim_id if present
        if (claimId) {
            window.location.href = `/upload/step1?claim_id=${claimId}`
        } else {
            window.location.href = '/upload/step1'
        }
    }, [])

    return (
        <div className="min-h-screen flex items-center justify-center">
            <div className="text-xl">Redirecting...</div>
        </div>
    )
}
