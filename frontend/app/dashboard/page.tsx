'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import AdvancedChart from '@/components/charting/AdvancedChart'
import PortfolioAnalytics from '@/components/portfolio/PortfolioAnalytics'
import Positions from '@/components/positions/Positions'
import SignalFeed from '@/components/signals/SignalFeed'
import TradeHistory from '@/components/trades/TradeHistory'
import Backtesting from '@/components/backtesting/Backtesting'
import { getPublicApiUrl } from '@/lib/runtime'

const API_URL = getPublicApiUrl()

type Tab = 'dashboard' | 'backtest' | 'signals' | 'positions' | 'history' | 'settings'

export default function DashboardPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')
  const [user, setUser] = useState<{ email?: string } | null>(null)

  const fetchUser = useCallback(async () => {
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setUser(data)
      } else {
        localStorage.removeItem('token')
        router.push('/auth/login')
      }
    } catch {
      router.push('/auth/login')
    }
  }, [router])

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/auth/login')
      return
    }
    fetchUser()
  }, [router, fetchUser])

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    router.push('/')
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'backtest', label: 'Backtest' },
    { id: 'signals', label: 'Signals' },
    { id: 'positions', label: 'Positions' },
    { id: 'history', label: 'History' },
    { id: 'settings', label: 'Settings' },
  ]

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="text-xl font-bold text-emerald-400">UltraCore</div>
          <div className="flex items-center gap-4">
            <span className="text-slate-400 text-sm">{user?.email}</span>
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm text-slate-300 hover:text-white transition"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <nav className="bg-slate-800 border-b border-slate-700 px-6">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium transition ${
                activeTab === tab.id
                  ? 'text-emerald-400 border-b-2 border-emerald-400'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Content */}
      <main className="p-6">
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
                <h2 className="text-lg font-semibold mb-4">Live Chart</h2>
                <AdvancedChart />
              </div>
              <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
                <h2 className="text-lg font-semibold mb-4">Portfolio</h2>
                <PortfolioAnalytics />
              </div>
            </div>
            <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
              <h2 className="text-lg font-semibold mb-4">Recent Signals</h2>
              <SignalFeed />
            </div>
          </div>
        )}

        {activeTab === 'backtest' && (
          <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Strategy Backtesting</h2>
            <Backtesting />
          </div>
        )}

        {activeTab === 'signals' && (
          <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">AI Trading Signals</h2>
            <SignalFeed />
          </div>
        )}

        {activeTab === 'positions' && (
          <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Open Positions</h2>
            <Positions />
          </div>
        )}

        {activeTab === 'history' && (
          <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Trade History</h2>
            <TradeHistory />
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Settings</h2>
            <p className="text-slate-400">API key configuration and account settings coming soon.</p>
          </div>
        )}
      </main>
    </div>
  )
}
