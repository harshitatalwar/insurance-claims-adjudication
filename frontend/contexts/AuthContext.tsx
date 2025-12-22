'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'
import { useRouter } from 'next/navigation'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

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
    login: (email: string, password: string) => Promise<void>
    register: (data: RegisterData) => Promise<void>
    logout: () => void
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
    const [isLoading, setIsLoading] = useState(true)
    const router = useRouter()

    // Initialize auth state from localStorage
    useEffect(() => {
        const storedToken = localStorage.getItem('access_token')
        if (storedToken) {
            setToken(storedToken)
            fetchUserData(storedToken)
        } else {
            setIsLoading(false)
        }
    }, [])

    const fetchUserData = async (accessToken: string) => {
        try {
            // 1. Get user info
            const userResponse = await axios.get(`${API_BASE_URL}/api/auth/me`, {
                headers: { Authorization: `Bearer ${accessToken}` }
            })
            setUser(userResponse.data)
            console.log('✅ User fetched:', userResponse.data)

            // 2. Get policy holder info by email
            const policyHoldersResponse = await axios.get(`${API_BASE_URL}/api/policy-holders/`, {
                headers: { Authorization: `Bearer ${accessToken}` }
            })
            console.log('✅ Policy holders fetched:', policyHoldersResponse.data)

            const policyHolder = policyHoldersResponse.data.find(
                (ph: PolicyHolder) => ph.email === userResponse.data.email
            )

            if (policyHolder) {
                setPolicyHolder(policyHolder)
                console.log('✅ Policy holder set:', policyHolder.policy_holder_id)
            } else {
                console.error('❌ No policy holder found for email:', userResponse.data.email)
            }
        } catch (error) {
            console.error('Failed to fetch user data:', error)
            // Token might be invalid, clear it
            localStorage.removeItem('access_token')
            setToken(null)
        } finally {
            setIsLoading(false)
        }
    }

    const login = async (email: string, password: string) => {
        try {
            // Use form data for OAuth2 password flow
            const formData = new FormData()
            formData.append('username', email)
            formData.append('password', password)

            const response = await axios.post(`${API_BASE_URL}/api/auth/login`, formData, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            })

            const accessToken = response.data.access_token
            localStorage.setItem('access_token', accessToken)
            setToken(accessToken)

            await fetchUserData(accessToken)
            router.push('/upload')
        } catch (error: any) {
            console.error('Login failed:', error)
            throw new Error(error.response?.data?.detail || 'Login failed')
        }
    }

    const register = async (data: RegisterData) => {
        try {
            // Register creates both auth user and policy holder in one call
            const authResponse = await axios.post(`${API_BASE_URL}/api/auth/register`, {
                full_name: data.full_name,
                email: data.email,
                phone: data.phone,
                date_of_birth: data.date_of_birth,
                password: data.password
            })

            const accessToken = authResponse.data.access_token
            localStorage.setItem('access_token', accessToken)
            setToken(accessToken)

            // Fetch complete user data
            await fetchUserData(accessToken)
            router.push('/upload')
        } catch (error: any) {
            console.error('Registration failed:', error)
            throw new Error(error.response?.data?.detail || 'Registration failed')
        }
    }

    const logout = () => {
        localStorage.removeItem('access_token')
        setToken(null)
        setUser(null)
        setPolicyHolder(null)
        router.push('/landing')
    }

    return (
        <AuthContext.Provider value={{ user, policyHolder, token, isLoading, login, register, logout }}>
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
