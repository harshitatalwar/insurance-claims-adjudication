'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, X, CheckCircle, AlertTriangle } from 'lucide-react'

interface FileUploadProps {
    uploadedFiles: File[]
    setUploadedFiles: (files: File[]) => void
}

interface UploadedFile extends File {
    id: string
    status: 'uploading' | 'success' | 'error'
    preview?: string
}

export default function FileUpload({ uploadedFiles, setUploadedFiles }: FileUploadProps) {
    const [files, setFiles] = useState<UploadedFile[]>([])

    const onDrop = useCallback((acceptedFiles: File[]) => {
        const newFiles = acceptedFiles.map(file => ({
            ...file,
            id: Math.random().toString(36).substr(2, 9),
            status: 'uploading' as const,
            preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
        }))

        setFiles(prev => [...prev, ...newFiles])
        setUploadedFiles([...uploadedFiles, ...acceptedFiles])

        // Simulate upload process
        newFiles.forEach(file => {
            setTimeout(() => {
                setFiles(prev => prev.map(f =>
                    f.id === file.id ? { ...f, status: 'success' } : f
                ))
            }, 1000 + Math.random() * 2000)
        })
    }, [uploadedFiles, setUploadedFiles])

    const removeFile = (fileId: string) => {
        setFiles(prev => prev.filter(f => f.id !== fileId))
        // Also remove from parent component
        const fileToRemove = files.find(f => f.id === fileId)
        if (fileToRemove) {
            setUploadedFiles(uploadedFiles.filter(f => f.name !== fileToRemove.name))
        }
    }

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'image/*': ['.jpeg', '.jpg', '.png', '.gif'],
            'application/pdf': ['.pdf'],
            'application/msword': ['.doc'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
        },
        maxSize: 5 * 1024 * 1024, // 5MB
        multiple: true
    })

    return (
        <div className="insurance-card">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Upload Documents</h3>

            {/* Upload Zone */}
            <div
                {...getRootProps()}
                className={`upload-zone cursor-pointer ${isDragActive ? 'border-insurance-blue bg-blue-50' : ''
                    }`}
            >
                <input {...getInputProps()} />
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />

                {isDragActive ? (
                    <p className="text-insurance-blue font-medium">Drop the files here...</p>
                ) : (
                    <div className="text-center">
                        <p className="text-gray-600 font-medium mb-2">
                            Drag & drop your documents here, or click to browse
                        </p>
                        <p className="text-sm text-gray-500">
                            Supports: JPG, PNG, PDF, DOC, DOCX (Max 5MB each)
                        </p>
                    </div>
                )}
            </div>

            {/* Uploaded Files List */}
            {files.length > 0 && (
                <div className="mt-6">
                    <h4 className="text-sm font-medium text-gray-900 mb-3">Uploaded Documents</h4>
                    <div className="space-y-3">
                        {files.map((file) => (
                            <div key={file.id} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                                <div className="flex-shrink-0">
                                    {file.preview ? (
                                        <img
                                            src={file.preview}
                                            alt={file.name}
                                            className="w-10 h-10 object-cover rounded"
                                        />
                                    ) : (
                                        <File className="w-10 h-10 text-gray-400" />
                                    )}
                                </div>

                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                                    <p className="text-sm text-gray-500">
                                        {(file.size / 1024 / 1024).toFixed(2)} MB
                                    </p>
                                </div>

                                <div className="flex items-center space-x-2">
                                    {file.status === 'uploading' && (
                                        <div className="w-5 h-5 border-2 border-insurance-blue border-t-transparent rounded-full animate-spin" />
                                    )}
                                    {file.status === 'success' && (
                                        <CheckCircle className="w-5 h-5 text-green-500" />
                                    )}
                                    {file.status === 'error' && (
                                        <AlertTriangle className="w-5 h-5 text-red-500" />
                                    )}

                                    <button
                                        onClick={() => removeFile(file.id)}
                                        className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Upload Summary */}
            {files.length > 0 && (
                <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
                    <p className="text-sm text-green-800">
                        <CheckCircle className="w-4 h-4 inline mr-2" />
                        {files.filter(f => f.status === 'success').length} of {files.length} documents uploaded successfully
                    </p>
                </div>
            )}
        </div>
    )
}
