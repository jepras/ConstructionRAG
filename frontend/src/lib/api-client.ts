import { createClient } from './supabase'

export interface ApiResponse<T> {
  data?: T
  error?: string
  status: number
}

export interface AuthResponse {
  success: boolean
  message: string
  access_token?: string
  refresh_token?: string
  user_id?: string
  email?: string
  expires_at?: string
}

export interface User {
  id: string
  email: string
  profile?: {
    id: string
    email: string
    full_name?: string
    created_at: string
    updated_at: string
  }
}

export class ApiClient {
  private baseURL: string

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL!
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    
    return session?.access_token 
      ? { Authorization: `Bearer ${session.access_token}` }
      : {}
  }

  private async request<T>(
    endpoint: string, 
    options?: RequestInit & { params?: Record<string, unknown> }
  ): Promise<T> {
    const url = new URL(endpoint, this.baseURL)
    
    if (options?.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value))
        }
      })
    }

    const response = await fetch(url.toString(), {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`API Error ${response.status}: ${errorText}`)
    }

    return response.json()
  }

  // Auth methods
  async signUp(email: string, password: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async signIn(email: string, password: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/auth/signin', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async signOut(): Promise<AuthResponse> {
    const headers = await this.getAuthHeaders()
    return this.request<AuthResponse>('/api/auth/signout', {
      method: 'POST',
      headers,
    })
  }

  async getCurrentUser(): Promise<User> {
    const headers = await this.getAuthHeaders()
    return this.request<User>('/api/auth/me', {
      headers,
    })
  }

  async refreshToken(refreshToken: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  }

  async resetPassword(email: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }
}

export const apiClient = new ApiClient()