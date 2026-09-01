import type { Alert } from '../types'

interface Props {
  alerts: Alert[]
}

const severityIcon: Record<string, string> = {
  critical: '🔴',
  warning: '🟡',
  info: '🔵',
}

export function AlertsPanel({ alerts }: Props) {
  return (
    <div className="panel alerts-panel">
      <div className="panel-header">
        <h2>Monitoring Alerts</h2>
        <span className="badge">{alerts.length}</span>
      </div>
      <div className="panel-body">
        {alerts.length === 0 ? (
          <p className="empty-state">No active alerts — all systems normal</p>
        ) : (
          <ul className="alert-list">
            {alerts.map((alert) => (
              <li key={alert.id} className={`alert-item ${alert.severity}`}>
                <span className="alert-icon">{severityIcon[alert.severity] ?? '⚪'}</span>
                <div className="alert-content">
                  <span className="alert-type">{alert.alert_type.replace('_', ' ')}</span>
                  <p className="alert-message">{alert.message}</p>
                  <span className="alert-time">
                    {new Date(alert.created_at).toLocaleTimeString()}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
