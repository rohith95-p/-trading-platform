'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { getPublicApiUrl } from '@/lib/runtime'

const API_URL = getPublicApiUrl()

export default function LoginPage() {
  const router = useRouter()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await axios.post(`${API_URL}/auth/login`, form)
      localStorage.setItem('token', res.data.access_token)
      localStorage.setItem('refresh_token', res.data.refresh_token)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleOAuth = (provider: 'google' | 'github') => {
    window.location.href = `${API_URL}/auth/oauth/${provider}`
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <Link href="/" className="block text-emerald-400 hover:text-emerald-300 mb-8">
          ← Back to home
        </Link>
        
        <div className="bg-slate-800 p-8 rounded-xl border border-slate-700">
          <h1 className="text-2xl font-bold mb-6">Welcome Back</h1>
          
          <div className="space-y-3 mb-6">
            <button
              onClick={() => handleOAuth('google')}
              className="w-full py-3 px-4 bg-white text-gray-800 hover:bg-gray-100 rounded-lg font-medium flex items-center justify-center gap-3 transition"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>
            <button
              onClick={() => handleOAuth('github')}
              className="w-full py-3 px-4 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium flex items-center justify-center gap-3 transition"
            >
              <svg className="w-5 h-5" fill="white" viewBox="0 0 24 24">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-.08-.69.275-1.02.765-.285 1.62.335 1.62.335.945-.795 1.605-1.53 1.605-1.53.045-.705.45-1.29.45-1.29.585.33 1.155.33 1.155.33 1.02.885 2.265.45 2.685.345.105-.615.45-1.065.45-1.065 1.125-.795.735-2.025.735-2.025.135-.705.36-1.065.36-1.065.48.345.885 1.065.885 1.065 3.09 4.665 7.785.345 7.785.345 0 6.075-4.95 6.075-4.95s1.32.015 2.01.945c-.06-.375-.18-.975-.18-.975S23.55 4.92 23.55 0s-5.37 0-5.37 0"/>
              </svg>
              Continue with GitHub
            </button>
          </div>
          
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="bg-slate-800 px-4 text-slate-500">or with email</span>
            </div>
          </div>
          
          {error && (
            <div className="bg-red-500/20 border border-red-500 text-red-400 p-3 rounded-lg mb-4">
              {error}
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-2">Email</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:border-emerald-500"
                placeholder="you@example.com"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-2">Password</label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:border-emerald-500"
                placeholder="••••••••"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-600 rounded-lg font-semibold transition"
            >
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>
          
          <div className="mt-6 text-center text-slate-400">
            <Link href="/auth/signup" className="text-emerald-400 hover:text-emerald-300">
              Sign up
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
