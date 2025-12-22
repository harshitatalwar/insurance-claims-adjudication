'use client'

import { CheckCircle, Circle, AlertCircle } from 'lucide-react'

interface DocumentItem {
    id: string
    title: string
    description: string
    required: boolean
    uploaded: boolean
}

export default function DocumentChecklist() {
    const documents: DocumentItem[] = [
        {
            id: 'prescription',
            title: 'Medical Prescription',
            description: 'Original prescription from registered doctor with diagnosis and medicines prescribed',
            required: true,
            uploaded: false
        },
        {
            id: 'bill',
            title: 'Medical Bills/Receipts',
            description: 'Original bills and receipts from hospital/clinic with proper stamps and signatures',
            required: true,
            uploaded: false
        },
        {
            id: 'diagnostic',
            title: 'Diagnostic Test Reports',
            description: 'Lab reports, X-rays, or other diagnostic test results (if applicable)',
            required: false,
            uploaded: false
        },
        {
            id: 'pharmacy',
            title: 'Pharmacy Bills',
            description: 'Medicine purchase receipts with batch numbers and expiry dates',
            required: true,
            uploaded: false
        },
        {
            id: 'identity',
            title: 'Identity Proof',
            description: 'Copy of Aadhaar card, PAN card, or other government-issued ID',
            required: true,
            uploaded: false
        },
        {
            id: 'policy',
            title: 'Policy Document',
            description: 'Copy of insurance policy or employee ID card',
            required: true,
            uploaded: false
        }
    ]

    return (
        <div className="insurance-card">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900">Claim Document Checklist</h3>
                <span className="text-sm text-gray-500">
                    {documents.filter(d => d.uploaded).length} of {documents.filter(d => d.required).length} required
                </span>
            </div>

            <div className="space-y-1">
                {documents.map((doc) => (
                    <div key={doc.id} className="document-checklist-item">
                        <div className="flex-shrink-0 mt-1">
                            {doc.uploaded ? (
                                <CheckCircle className="w-5 h-5 text-green-500" />
                            ) : doc.required ? (
                                <Circle className="w-5 h-5 text-gray-400" />
                            ) : (
                                <Circle className="w-5 h-5 text-gray-300" />
                            )}
                        </div>

                        <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2">
                                <p className="text-sm font-medium text-gray-900">{doc.title}</p>
                                {doc.required && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                                        Required
                                    </span>
                                )}
                            </div>
                            <p className="text-sm text-gray-500 mt-1">{doc.description}</p>
                        </div>
                    </div>
                ))}
            </div>

            {/* Important Notes */}
            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <div className="flex items-start space-x-2">
                    <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                    <div>
                        <p className="text-sm font-medium text-blue-800">Document Guidelines</p>
                        <ul className="text-sm text-blue-700 mt-2 space-y-1">
                            <li>• All documents must be clear and legible</li>
                            <li>• Doctor's registration number must be visible</li>
                            <li>• Patient name must match policy records</li>
                            <li>• Treatment dates should be consistent across documents</li>
                            <li>• Maximum file size: 5MB per document</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    )
}
