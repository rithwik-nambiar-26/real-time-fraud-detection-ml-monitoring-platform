import { useEffect, useState } from 'react'
import type { Alert, MetricsSummary, TransactionRecord } from './types'
import { connectTransactionStream, getAlerts, getMetrics, getTransactions } from './api'
import { MetricCards } from './components/MetricCards'
import { AlertsPanel } from './components/AlertsPanel'
import { TransactionFeed } from './components/TransactionFeed'
import { ScoreChart } from './components/ScoreChart'
import { RiskChart } from './components/RiskChart'
import './App.css'

function App() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null)
  const [transactions, setTransactions] = useState<TransactionRecord[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = async () => {
    try {
      const [m, txns, alts] = await Promise.all([
        getMetrics(),
        getTransactions(30),
        getAlerts(),
      ])
      setMetrics(m)
      setTransactions(txns)
      setAlerts(alts)
      setError(null)
    } catch (e) {
      setError('Unable to connect to backend. Start the API server on port 8000.')
    }
  }

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 10000)

    let ws: WebSocket | null = null
    try {
      ws = connectTransactionStream((txn) => {
        setConnected(true)
        setTransactions((prev) => [txn as TransactionRecord, ...prev].slice(0, 50))
      })
      ws.onopen = () => setConnected(true)
      ws.onclose = () => setConnected(false)
      ws.onerror = () => setConnected(false)
    } catch {
      setConnected(false)
    }

    return () => {
      clearInterval(interval)
      ws?.close()
    }
  }, [])

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <div className="logo">🛡️</div>
          <div>
            <h1>Fraud Detection Platform</h1>
            <p className="subtitle">Real-time ML monitoring & scoring</p>
          </div>
        </div>
        <div className="header-right">
          <span className={`status-dot ${connected ? 'online' : 'offline'}`} />
          <span className="status-text">{connected ? 'Live' : 'Polling'}</span>
          {metrics && <span className="model-badge">{metrics.model_version}</span>}
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {metrics && <MetricCards metrics={metrics} />}

      <div className="charts-row">
        {metrics && (
          <>
            <ScoreChart distribution={metrics.score_distribution} />
            <RiskChart distribution={metrics.risk_distribution} />
          </>
        )}
      </div>

      <div className="panels-row">
        <TransactionFeed transactions={transactions} />
        <AlertsPanel alerts={alerts} />
      </div>
    </div>
  )
}

export default App
