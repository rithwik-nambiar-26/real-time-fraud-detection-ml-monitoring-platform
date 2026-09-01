import type { Alert, MetricsSummary, TransactionRecord } from './types'

const API_BASE = '/api/v1'

async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`API error: ${resp.status}`)
  return resp.json()
}

export async function getMetrics(windowMinutes = 60): Promise<MetricsSummary> {
  return fetchJson(`${API_BASE}/metrics?window_minutes=${windowMinutes}`)
}

export async function getTransactions(limit = 50, fraudOnly = false): Promise<TransactionRecord[]> {
  return fetchJson(`${API_BASE}/transactions?limit=${limit}&fraud_only=${fraudOnly}`)
}

export async function getAlerts(): Promise<Alert[]> {
  return fetchJson(`${API_BASE}/alerts`)
}

export async function getHealth() {
  const resp = await fetch('/health')
  return resp.json()
}

export function connectTransactionStream(onMessage: (txn: TransactionRecord) => void): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws/transactions`)

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (msg.type === 'transaction') {
      onMessage(msg.data)
    }
  }

  return ws
}
