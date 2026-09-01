import type { MetricsSummary } from '../types'

interface Props {
  metrics: MetricsSummary
}

export function MetricCards({ metrics }: Props) {
  const cards = [
    {
      label: 'Transactions Scored',
      value: metrics.total_scored.toLocaleString(),
      sub: `Last ${metrics.window_minutes} min`,
      color: 'blue',
    },
    {
      label: 'Fraud Rate',
      value: `${(metrics.fraud_rate * 100).toFixed(1)}%`,
      sub: metrics.fraud_rate > 0.15 ? 'Elevated' : 'Normal',
      color: metrics.fraud_rate > 0.15 ? 'red' : 'green',
    },
    {
      label: 'Avg Latency',
      value: `${metrics.avg_latency_ms.toFixed(0)}ms`,
      sub: `P95: ${metrics.p95_latency_ms.toFixed(0)}ms`,
      color: metrics.p95_latency_ms > 500 ? 'yellow' : 'green',
    },
    {
      label: 'Throughput',
      value: `${metrics.throughput_per_minute.toFixed(1)}/min`,
      sub: 'Scoring rate',
      color: 'blue',
    },
    {
      label: 'Drift Score',
      value: metrics.drift_score.toFixed(3),
      sub: metrics.drift_detected ? 'Drift detected' : 'Stable',
      color: metrics.drift_detected ? 'red' : 'green',
    },
  ]

  return (
    <div className="metric-cards">
      {cards.map((card) => (
        <div key={card.label} className={`metric-card ${card.color}`}>
          <span className="metric-label">{card.label}</span>
          <span className="metric-value">{card.value}</span>
          <span className="metric-sub">{card.sub}</span>
        </div>
      ))}
    </div>
  )
}
