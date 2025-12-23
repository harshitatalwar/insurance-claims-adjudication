import axios, { AxiosInstance, AxiosError } from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

// Create axios instance with base configuration
const apiClient: AxiosInstance = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor - automatically inject auth token
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor - centralized error handling
apiClient.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
        // Handle 401 Unauthorized - token expired or invalid
        if (error.response?.status === 401) {
            localStorage.removeItem('access_token')
            // Only redirect if not already on login/register page
            if (typeof window !== 'undefined' &&
                !window.location.pathname.includes('/login') &&
                !window.location.pathname.includes('/register')) {
                window.location.href = '/login'
            }
        }

        // Handle 403 Forbidden
        if (error.response?.status === 403) {
            console.error('Access forbidden:', error.response.data)
        }

        // Handle 500 Server Error
        if (error.response?.status === 500) {
            console.error('Server error:', error.response.data)
        }

        return Promise.reject(error)
    }
)

// Type definitions
export interface LoginRequest {
    email: string
    password: string
}

export interface RegisterRequest {
    full_name: string
    email: string
    phone: string
    date_of_birth: string
    password: string
}

export interface TokenResponse {
    access_token: string
    token_type: string
}

export interface User {
    email: string
    full_name: string
    role: string
}

export interface PolicyHolder {
    policy_holder_id: string
    policy_holder_name: string
    email: string
    phone: string
    annual_limit: number
    annual_limit_used: number
    date_of_birth: string
}

export interface CreateClaimRequest {
    policy_holder_id: string
    claimed_amount: number
    treatment_type: string
    provider_network: boolean
    treatment_date: string
}

export interface Claim {
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

export interface PresignedUrlRequest {
    claim_id: string
    filename: string
    document_type: string
}

export interface PresignedUrlResponse {
    file_id: string
    upload_url: string
}

export interface DocumentStatus {
    file_id: string
    filename: string
    document_type: string
    status: 'uploaded' | 'processing' | 'processed' | 'failed'
    uploaded_at?: string
    confidence_score?: number
    extracted_data?: any
}

// API Client - organized by domain
export const api = {
    // Authentication endpoints
    auth: {
        /**
         * Login with email and password
         * Uses form-data format for OAuth2 compatibility
         */
        login: async (email: string, password: string): Promise<TokenResponse> => {
            const formData = new FormData()
            formData.append('username', email)
            formData.append('password', password)

            const response = await axios.post(
                `${API_BASE_URL}/api/auth/login`,
                formData,
                {
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                }
            )
            return response.data
        },

        /**
         * Register new user and policy holder
         */
        register: async (data: RegisterRequest): Promise<TokenResponse> => {
            const response = await apiClient.post('/api/auth/register', data)
            return response.data
        },

        /**
         * Get current user information
         */
        me: async (): Promise<User> => {
            const response = await apiClient.get('/api/auth/me')
            return response.data
        },

        /**
         * Logout (client-side only - clears token)
         */
        logout: () => {
            localStorage.removeItem('access_token')
        },
    },

    // Claims endpoints
    claims: {
        /**
         * Create a new claim
         */
        create: async (data: CreateClaimRequest): Promise<Claim> => {
            const response = await apiClient.post('/api/claims/', data)
            return response.data
        },

        /**
         * Get all claims for current user
         */
        list: async (): Promise<Claim[]> => {
            const response = await apiClient.get('/api/claims/')
            return response.data
        },

        /**
         * Get specific claim by ID
         */
        get: async (claimId: string): Promise<Claim> => {
            const response = await apiClient.get(`/api/claims/${claimId}`)
            return response.data
        },

        /**
         * Trigger adjudication for a claim
         */
        adjudicate: async (claimId: string): Promise<any> => {
            const response = await apiClient.post(`/api/claims/${claimId}/adjudicate`)
            return response.data
        },

        /**
         * Delete a claim
         */
        delete: async (claimId: string): Promise<void> => {
            await apiClient.delete(`/api/claims/${claimId}`)
        },
    },

    // Documents endpoints
    documents: {
        /**
         * Get presigned URL for document upload
         */
        getPresignedUrl: async (data: PresignedUrlRequest): Promise<PresignedUrlResponse> => {
            const response = await apiClient.post('/api/documents/upload', data)
            return response.data
        },

        /**
         * Upload file to MinIO using presigned URL
         */
        uploadToMinIO: async (uploadUrl: string, file: File): Promise<void> => {
            await axios.put(uploadUrl, file, {
                headers: {
                    'Content-Type': file.type || 'application/octet-stream'
                }
            })
        },

        /**
         * Trigger OCR processing for uploaded document
         */
        triggerProcessing: async (fileId: string): Promise<any> => {
            const response = await apiClient.post(`/api/documents/${fileId}/process`)
            return response.data
        },

        /**
         * Get all documents for a claim
         */
        getStatus: async (claimId: string): Promise<DocumentStatus[]> => {
            const response = await apiClient.get(`/api/documents/status?claim_id=${claimId}`)
            return response.data
        },

        /**
         * Get single document status
         */
        getDocumentStatus: async (fileId: string): Promise<DocumentStatus> => {
            const response = await apiClient.get(`/api/documents/${fileId}`)
            return response.data
        },
    },

    // Policy Holders endpoints
    policyHolders: {
        /**
         * Get all policy holders (admin only)
         */
        list: async (): Promise<PolicyHolder[]> => {
            const response = await apiClient.get('/api/policy-holders/')
            return response.data
        },

        /**
         * Get specific policy holder
         */
        get: async (policyHolderId: string): Promise<PolicyHolder> => {
            const response = await apiClient.get(`/api/policy-holders/${policyHolderId}`)
            return response.data
        },

        /**
         * Update policy holder
         */
        update: async (policyHolderId: string, data: Partial<PolicyHolder>): Promise<PolicyHolder> => {
            const response = await apiClient.put(`/api/policy-holders/${policyHolderId}`, data)
            return response.data
        },

        /**
         * Delete policy holder (admin only)
         */
        delete: async (policyHolderId: string): Promise<void> => {
            await apiClient.delete(`/api/policy-holders/${policyHolderId}`)
        },
    },
}

export default apiClient
