export interface ScoreResponse {
  transaction_id: string
  fraud_score: number
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  is_fraud: boolean
  latency_ms: number
  model_version: string
  scored_at: string
}

export interface TransactionRecord extends ScoreResponse {
  amount: number
  merchant_category: string
  features: Record<string, unknown>
}

export interface MetricsSummary {
  total_scored: number
  fraud_rate: number
  avg_latency_ms: number
  p95_latency_ms: number
  throughput_per_minute: number
  model_version: string
  drift_score: number
  drift_detected: boolean
  score_distribution: Record<string, number>
  risk_distribution: Record<string, number>
  window_minutes: number
}

export interface Alert {
  id: string
  alert_type: string
  severity: string
  message: string
  value: number
  threshold: number
  created_at: string
  resolved: boolean
}

export interface HealthStatus {
  status: string
  model_loaded: boolean
  model_version: string | null
  database_connected: boolean
}
