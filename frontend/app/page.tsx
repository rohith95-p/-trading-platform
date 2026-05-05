import type { Metadata } from 'next'
import './globals.css'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'UltraCore - AI-Powered Trading Platform',
  description: 'Multi-exchange algorithmic trading platform with 21+ technical indicators, AI news classification, and DRL agents.',
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Hero Section */}
      <header className="container mx-auto px-6 py-20">
        <nav className="flex items-center justify-between mb-20">
          <div className="text-2xl font-bold text-emerald-400">UltraCore</div>
          <div className="flex gap-6">
            <Link href="/auth/login" className="px-4 py-2 text-slate-300 hover:text-white transition">
              Login
            </Link>
            <Link href="/auth/signup" className="px-6 py-2 bg-emerald-500 hover:bg-emerald-600 rounded-lg font-medium transition">
              Get Started Free
            </Link>
          </div>
        </nav>

        <div className="max-w-4xl">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
            Trade Smarter with
            <span className="text-emerald-400"> AI Intelligence</span>
          </h1>
          <p className="text-xl text-slate-400 mb-10 max-w-2xl">
            Multi-exchange algorithmic trading platform combining 21+ technical indicators,
            real-time news sentiment analysis, and deep reinforcement learning agents.
          </p>
          <div className="flex gap-4">
            <Link href="/auth/signup" className="px-8 py-4 bg-emerald-500 hover:bg-emerald-600 rounded-lg font-semibold text-lg transition">
              Start Trading Free
            </Link>
            <Link href="/dashboard" className="px-8 py-4 border border-slate-600 hover:border-slate-500 rounded-lg font-medium text-lg transition">
              View Dashboard
            </Link>
          </div>
        </div>
      </header>

      {/* Features Grid */}
      <section className="container mx-auto px-6 py-20 bg-slate-800/50">
        <h2 className="text-3xl font-bold text-center mb-16">Platform Features</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-slate-800 p-8 rounded-xl border border-slate-700">
            <div className="text-4xl mb-4">TA</div>
            <h3 className="text-xl font-semibold mb-3">21+ Technical Indicators</h3>
            <p className="text-slate-400">
              EMA, RSI, MACD, Bollinger Bands, Ichimoku Cloud, Stochastic, and more...
            </p>
          </div>
          <div className="bg-slate-800 p-8 rounded-xl border border-slate-700">
            <div className="text-4xl mb-4">AI</div>
            <h3 className="text-xl font-semibold mb-3">AI News Classification</h3>
            <p className="text-slate-400">
              Real-time sentiment analysis powered by Claude API
            </p>
          </div>
          <div className="bg-slate-800 p-8 rounded-xl border border-slate-700">
            <div className="text-4xl mb-4">RL</div>
            <h3 className="text-xl font-semibold mb-3">DRL Trading Agent</h3>
            <p className="text-slate-400">
              Deep reinforcement learning with PPO and constitutional guardrails
            </p>
          </div>
          <div className="bg-slate-800 p-8 rounded-xl border border-slate-700">
            <div className="text-4xl mb-4">EX</div>
            <h3 className="text-xl font-semibold mb-3">Multi-Exchange</h3>
            <p className="text-slate-400">
              Binance, Alpaca, Hyperliquid, Kraken, dYdX, Kalshi, Polymarket
            </p>
          </div>
          <div className="bg-slate-800 p-8 rounded-xl border border-slate-700">
            <div className="text-4xl mb-4">PT</div>
            <h3 className="text-xl font-semibold mb-3">Paper Trading</h3>
            <p className="text-slate-400">
              Test strategies risk-free before going live
            </p>
          </div>
          <div className="bg-slate-800 p-8 rounded-xl border border-slate-700">
            <div className="text-4xl mb-4">BT</div>
            <h3 className="text-xl font-semibold mb-3">Vectorized Backtesting</h3>
            <p className="text-slate-400">
              Fast historical strategy testing with detailed metrics
            </p>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="container mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-center mb-4">Simple Pricing</h2>
        <p className="text-slate-400 text-center mb-16">Start free, upgrade when you need more</p>
        <div className="max-w-md mx-auto bg-slate-800 p-10 rounded-xl border border-emerald-500">
          <div className="text-sm text-emerald-400 font-medium mb-2">Early Access</div>
          <div className="text-5xl font-bold mb-2">$0<span className="text-xl font-normal text-slate-400">/month</span></div>
          <p className="text-slate-400 mb-8">Perfect for getting started</p>
          <ul className="space-y-4 mb-10">
            <li className="flex items-center gap-3">
              <span className="text-emerald-400">OK</span>
              <span>Paper trading on all exchanges</span>
            </li>
            <li className="flex items-center gap-3">
              <span className="text-emerald-400">OK</span>
              <span>21+ technical indicators</span>
            </li>
            <li className="flex items-center gap-3">
              <span className="text-emerald-400">OK</span>
              <span>AI news classification</span>
            </li>
            <li className="flex items-center gap-3">
              <span className="text-emerald-400">OK</span>
              <span>Multi-agent simulation</span>
            </li>
            <li className="flex items-center gap-3">
              <span className="text-emerald-400">OK</span>
              <span>Vectorized backtesting</span>
            </li>
          </ul>
          <Link href="/auth/signup" className="block w-full py-4 bg-emerald-500 hover:bg-emerald-600 rounded-lg font-semibold text-center transition">
            Get Started Free
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="container mx-auto px-6 py-12 border-t border-slate-800">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="text-xl font-bold text-emerald-400 mb-4 md:mb-0">UltraCore</div>
          <div className="text-slate-500 text-sm">
            (c) 2024 UltraCore Trading Platform. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}
