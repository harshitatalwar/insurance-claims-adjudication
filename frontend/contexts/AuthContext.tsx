'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '../utils/api-client'

interface User {
    email: string
    full_name: string
    role: string
}

interface PolicyHolder {
    policy_holder_id: string
    policy_holder_name: string
    email: string
    phone: string
    annual_limit: number
    annual_limit_used: number
    date_of_birth: string
}

interface AuthContextType {
    user: User | null
    policyHolder: PolicyHolder | null
    token: string | null
    isLoading: boolean
    isInitialized: boolean
    login: (email: string, password: string) => Promise<void>
    register: (data: RegisterData) => Promise<void>
    logout: () => void
    initializeAuth: () => Promise<void>
}

interface RegisterData {
    full_name: string
    email: string
    password: string
    phone: string
    date_of_birth: string
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [policyHolder, setPolicyHolder] = useState<PolicyHolder | null>(null)
    const [token, setToken] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(false)
    const [isInitialized, setIsInitialized] = useState(false)
    const router = useRouter()

    // Initialize token from localStorage on mount (but don't validate it)
    useEffect(() => {
        const storedToken = localStorage.getItem('access_token')
        if (storedToken) {
            setToken(storedToken)
        }
    }, [])

    const fetchUserData = async (accessToken: string) => {
        try {
            // Set token in localStorage so API client can use it
            localStorage.setItem('access_token', accessToken)

            // 1. Get user info
            console.log('🔍 Fetching user data...')
            const userData = await api.auth.me()
            setUser(userData)
            console.log('✅ User fetched:', userData)

            // 2. Get policy holder info by email
            console.log('🔍 Fetching policy holders...')
            const policyHolders = await api.policyHolders.list()
            console.log('✅ Policy holders fetched:', policyHolders)

            const policyHolder = policyHolders.find(
                (ph: PolicyHolder) => ph.email === userData.email
            )

            if (policyHolder) {
                setPolicyHolder(policyHolder)
                console.log('✅ Policy holder set:', policyHolder.policy_holder_id)
            } else {
                console.error('❌ No policy holder found for email:', userData.email)
                throw new Error('Policy holder not found for this email')
            }
        } catch (error: any) {
            console.error('❌ fetchUserData error:', error)

            // Clear auth state on error
            if (error.response?.status === 401) {
                localStorage.removeItem('access_token')
                setToken(null)
                setUser(null)
                setPolicyHolder(null)
            }

            // Re-throw the error so register/login know it failed
            throw error
        } finally {
            setIsLoading(false)
        }
    }

    // Lazy initialization - only called by protected routes
    const initializeAuth = async () => {
        // Skip if already initialized or currently loading
        if (isInitialized || isLoading) {
            return
        }

        setIsLoading(true)

        const storedToken = localStorage.getItem('access_token')
        if (storedToken) {
            setToken(storedToken)
            await fetchUserData(storedToken)
        } else {
            setIsLoading(false)
        }

        setIsInitialized(true)
    }

    const login = async (email: string, password: string) => {
        try {
            console.log('🔐 Starting login...')
            const response = await api.auth.login(email, password)
            console.log('✅ Login API response:', response)

            const accessToken = response.access_token
            localStorage.setItem('access_token', accessToken)
            setToken(accessToken)
            console.log('✅ Token saved to localStorage')

            // Reset initialization flag and fetch user data
            setIsInitialized(false)
            setIsLoading(true)
            console.log('🔍 Fetching user data...')

            await fetchUserData(accessToken)
            console.log('✅ User data fetched successfully')

            setIsInitialized(true)
            console.log('✅ Auth initialized')

            // Redirect after user data is loaded
            console.log('🚀 Redirecting to /upload...')
            router.push('/upload')
            console.log('✅ Redirect called')
        } catch (error: any) {
            console.error('❌ Login failed:', error)
            setIsLoading(false)
            throw new Error(error.response?.data?.detail || 'Login failed')
        }
    }

    const register = async (data: RegisterData) => {
        try {
            // Register creates both auth user and policy holder in one call
            const response = await api.auth.register(data)
            const accessToken = response.access_token
            localStorage.setItem('access_token', accessToken)
            setToken(accessToken)

            // Reset initialization flag and fetch user data
            setIsInitialized(false)
            setIsLoading(true)
            await fetchUserData(accessToken)
            setIsInitialized(true)

            // Redirect after user data is loaded
            router.push('/upload')
        } catch (error: any) {
            console.error('Registration failed:', error)
            setIsLoading(false)
            throw new Error(error.response?.data?.detail || 'Registration failed')
        }
    }

    const logout = () => {
        api.auth.logout()
        setToken(null)
        setUser(null)
        setPolicyHolder(null)
        setIsInitialized(false)  // Reset initialization flag
        setIsLoading(false)
        router.push('/landing')
    }

    return (
        <AuthContext.Provider value={{ user, policyHolder, token, isLoading, isInitialized, login, register, logout, initializeAuth }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
