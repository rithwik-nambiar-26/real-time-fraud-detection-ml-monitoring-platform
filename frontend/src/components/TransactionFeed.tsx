import type { TransactionRecord } from '../types'

interface Props {
  transactions: TransactionRecord[]
}

const riskColors: Record<string, string> = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#f97316',
  critical: '#ef4444',
}

export function TransactionFeed({ transactions }: Props) {
  return (
    <div className="panel feed-panel">
      <div className="panel-header">
        <h2>Live Transaction Feed</h2>
        <span className="badge">{transactions.length}</span>
      </div>
      <div className="panel-body">
        {transactions.length === 0 ? (
          <p className="empty-state">
            Waiting for transactions… Run the simulator to populate data.
          </p>
        ) : (
          <table className="txn-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Amount</th>
                <th>Category</th>
                <th>Score</th>
                <th>Risk</th>
                <th>Status</th>
                <th>Latency</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((txn) => (
                <tr key={txn.transaction_id} className={txn.is_fraud ? 'fraud-row' : ''}>
                  <td className="txn-id">{txn.transaction_id.slice(0, 12)}</td>
                  <td>${txn.amount?.toFixed(2) ?? '—'}</td>
                  <td>{txn.merchant_category ?? '—'}</td>
                  <td>
                    <div className="score-bar-wrap">
                      <div
                        className="score-bar"
                        style={{
                          width: `${(txn.fraud_score * 100).toFixed(0)}%`,
                          background: riskColors[txn.risk_level] ?? '#888',
                        }}
                      />
                      <span>{(txn.fraud_score * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td>
                    <span
                      className="risk-badge"
                      style={{ background: riskColors[txn.risk_level] }}
                    >
                      {txn.risk_level}
                    </span>
                  </td>
                  <td>{txn.is_fraud ? '🚨 Fraud' : '✓ OK'}</td>
                  <td>{txn.latency_ms?.toFixed(0)}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
