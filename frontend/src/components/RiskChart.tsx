import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

interface Props {
  distribution: Record<string, number>
}

const COLORS: Record<string, string> = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#f97316',
  critical: '#ef4444',
}

export function RiskChart({ distribution }: Props) {
  const data = Object.entries(distribution).map(([name, value]) => ({ name, value }))

  if (data.length === 0) {
    return (
      <div className="panel chart-panel">
        <div className="panel-header"><h2>Risk Level Breakdown</h2></div>
        <p className="empty-state">No data yet</p>
      </div>
    )
  }

  return (
    <div className="panel chart-panel">
      <div className="panel-header">
        <h2>Risk Level Breakdown</h2>
      </div>
      <div className="chart-body">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={3}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={COLORS[entry.name] ?? '#64748b'} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
