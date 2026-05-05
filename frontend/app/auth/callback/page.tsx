'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

type CallbackState =
  | { status: 'loading'; message: string }
  | { status: 'error'; message: string }

export default function AuthCallbackPage() {
  const router = useRouter()
  const [state, setState] = useState<CallbackState>({
    status: 'loading',
    message: 'Finalizing sign-in...',
  })

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    const accessToken = params.get('access_token')
    const refreshToken = params.get('refresh_token')

    if (!accessToken || !refreshToken) {
      setState({
        status: 'error',
        message: 'Authentication callback is missing required tokens.',
      })
      return
    }

    localStorage.setItem('token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)

    const email = params.get('email')
    if (email) {
      localStorage.setItem('user_email', email)
    }

    router.replace('/dashboard')
  }, [router])

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-white">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-2xl shadow-slate-950/50">
        <h1 className="text-2xl font-semibold">UltraCore</h1>
        <p className="mt-3 text-sm text-slate-400">{state.message}</p>
        {state.status === 'loading' ? (
          <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-slate-800">
            <div className="h-full w-1/2 animate-pulse rounded-full bg-emerald-400" />
          </div>
        ) : (
          <button
            className="mt-6 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-emerald-400"
            onClick={() => router.replace('/auth/login')}
            type="button"
          >
            Back to login
          </button>
        )}
      </div>
    </div>
  )
}
