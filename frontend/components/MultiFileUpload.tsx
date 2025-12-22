'use client';

import { useState, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import Webcam from 'react-webcam';

interface FileUploadInfo {
    file: File;
    fileId: string;
    uploadUrl: string;
    objectName: string;
    status: 'pending' | 'uploading' | 'processing' | 'complete' | 'error';
    progress: number;
    extractedData?: any;
}

export function MultiFileUpload({ claimId }: { claimId: string }) {
    const [files, setFiles] = useState<FileUploadInfo[]>([]);
    const [showCamera, setShowCamera] = useState(false);
    const webcamRef = useRef<Webcam>(null);

    // Step 1: Get presigned URLs for all files
    const getPresignedURLs = async (filesToUpload: File[]) => {
        const response = await fetch('/api/upload/batch-presigned-urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                claim_id: claimId,
                files: filesToUpload.map(file => ({
                    filename: file.name,
                    content_type: file.type,
                    document_type: detectDocumentType(file.name)
                }))
            })
        });

        return response.json();
    };

    // Step 2: Upload files in parallel
    const uploadFiles = async (filesToUpload: File[]) => {
        // Get presigned URLs for all files
        const presignedURLs = await getPresignedURLs(filesToUpload);

        // Create file info objects
        const fileInfos: FileUploadInfo[] = filesToUpload.map((file, index) => ({
            file,
            fileId: presignedURLs[index].file_id,
            uploadUrl: presignedURLs[index].upload_url,
            objectName: presignedURLs[index].object_name,
            status: 'pending',
            progress: 0
        }));

        setFiles(prev => [...prev, ...fileInfos]);

        // Upload all files in parallel
        const uploadPromises = fileInfos.map(async (fileInfo, index) => {
            try {
                // Update status
                updateFileStatus(fileInfo.fileId, 'uploading', 0);

                // Upload to MinIO via presigned URL
                await fetch(fileInfo.uploadUrl, {
                    method: 'PUT',
                    body: fileInfo.file,
                    headers: {
                        'Content-Type': fileInfo.file.type
                    }
                });

                updateFileStatus(fileInfo.fileId, 'uploading', 100);

                // Notify backend that upload is complete
                const response = await fetch('/api/upload/upload-complete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        file_id: fileInfo.fileId,
                        object_name: fileInfo.objectName
                    })
                });

                updateFileStatus(fileInfo.fileId, 'processing', 100);

                // Poll for processing completion
                pollForCompletion(fileInfo.fileId);

            } catch (error) {
                console.error(`Upload failed for ${fileInfo.file.name}:`, error);
                updateFileStatus(fileInfo.fileId, 'error', 0);
            }
        });

        await Promise.all(uploadPromises);
    };

    // Step 3: Poll for OCR + Qdrant completion
    const pollForCompletion = async (fileId: string) => {
        const maxAttempts = 30; // 30 seconds
        let attempts = 0;

        const poll = setInterval(async () => {
            attempts++;

            try {
                const response = await fetch(`/api/documents/status/${fileId}`);
                const data = await response.json();

                if (data.status === 'processed') {
                    updateFileStatus(fileId, 'complete', 100, data.extracted_data);
                    clearInterval(poll);
                } else if (attempts >= maxAttempts) {
                    updateFileStatus(fileId, 'error', 100);
                    clearInterval(poll);
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 1000);
    };

    // Update file status
    const updateFileStatus = (
        fileId: string,
        status: FileUploadInfo['status'],
        progress: number,
        extractedData?: any
    ) => {
        setFiles(prev =>
            prev.map(f =>
                f.fileId === fileId
                    ? { ...f, status, progress, extractedData }
                    : f
            )
        );
    };

    // Detect document type from filename
    const detectDocumentType = (filename: string): string => {
        const lower = filename.toLowerCase();
        if (lower.includes('prescription') || lower.includes('rx')) return 'prescription';
        if (lower.includes('bill') || lower.includes('invoice')) return 'bill';
        if (lower.includes('report') || lower.includes('test')) return 'report';
        return 'other';
    };

    // Drag & drop handler
    const onDrop = async (acceptedFiles: File[]) => {
        await uploadFiles(acceptedFiles);
    };

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'image/*': ['.jpeg', '.jpg', '.png', '.heic'],
            'application/pdf': ['.pdf'],
            'text/plain': ['.txt']
        },
        maxSize: 10 * 1024 * 1024, // 10MB
        multiple: true
    });

    // Camera capture
    const capturePhoto = async () => {
        const imageSrc = webcamRef.current?.getScreenshot();
        if (imageSrc) {
            const blob = await fetch(imageSrc).then(r => r.blob());
            const file = new File([blob], `camera-${Date.now()}.jpg`, { type: 'image/jpeg' });
            await uploadFiles([file]);
            setShowCamera(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* Upload Zone */}
            <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}`}
            >
                <input {...getInputProps()} />
                <div className="space-y-2">
                    <p className="text-lg font-medium">
                        {isDragActive ? 'Drop files here...' : 'Drag & drop files or click to browse'}
                    </p>
                    <p className="text-sm text-gray-500">
                        Supports: Images (JPG, PNG, HEIC), PDF, TXT • Max 10MB per file
                    </p>
                </div>
            </div>

            {/* Camera Button */}
            <button
                onClick={() => setShowCamera(true)}
                className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
                📷 Capture Photo
            </button>

            {/* File List */}
            {files.length > 0 && (
                <div className="space-y-3">
                    <h3 className="font-semibold text-lg">Uploaded Files ({files.length})</h3>
                    {files.map(fileInfo => (
                        <div
                            key={fileInfo.fileId}
                            className="border rounded-lg p-4 space-y-2"
                        >
                            <div className="flex items-center justify-between">
                                <span className="font-medium">{fileInfo.file.name}</span>
                                <StatusBadge status={fileInfo.status} />
                            </div>

                            {/* Progress Bar */}
                            {fileInfo.status === 'uploading' && (
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                    <div
                                        className="bg-blue-600 h-2 rounded-full transition-all"
                                        style={{ width: `${fileInfo.progress}%` }}
                                    />
                                </div>
                            )}

                            {/* Extracted Data Preview */}
                            {fileInfo.status === 'complete' && fileInfo.extractedData && (
                                <div className="bg-green-50 p-3 rounded text-sm">
                                    <p className="font-medium text-green-800">✓ Extracted Data:</p>
                                    <pre className="text-xs mt-1 text-green-700">
                                        {JSON.stringify(fileInfo.extractedData, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Camera Modal */}
            {showCamera && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white p-6 rounded-lg max-w-lg">
                        <Webcam
                            ref={webcamRef}
                            screenshotFormat="image/jpeg"
                            className="rounded-lg w-full"
                        />
                        <div className="mt-4 flex gap-3">
                            <button
                                onClick={capturePhoto}
                                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                            >
                                Capture
                            </button>
                            <button
                                onClick={() => setShowCamera(false)}
                                className="flex-1 px-4 py-2 bg-gray-300 rounded-lg hover:bg-gray-400"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function StatusBadge({ status }: { status: FileUploadInfo['status'] }) {
    const styles = {
        pending: 'bg-gray-100 text-gray-700',
        uploading: 'bg-blue-100 text-blue-700',
        processing: 'bg-yellow-100 text-yellow-700',
        complete: 'bg-green-100 text-green-700',
        error: 'bg-red-100 text-red-700'
    };

    const labels = {
        pending: 'Pending',
        uploading: 'Uploading...',
        processing: 'Processing...',
        complete: 'Complete',
        error: 'Error'
    };

    return (
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${styles[status]}`}>
            {labels[status]}
        </span>
    );
}
