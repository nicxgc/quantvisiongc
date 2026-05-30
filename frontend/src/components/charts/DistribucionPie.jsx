import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { formatEuros } from '../../utils/formatters'

// Donut de distribución de la cartera por categoría (RF-26).
// Cada porción se pondera por el importe invertido en esa categoría.
export default function DistribucionPie({ data, alto = 280 }) {
  if (!Array.isArray(data) || data.length === 0) {
    return (
      <div style={{ height: alto, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999', fontSize: 13 }}>
        Sin datos
      </div>
    )
  }
  return (
    <ResponsiveContainer width="100%" height={alto}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={90}
          paddingAngle={2}
        >
          {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
        </Pie>
        <Tooltip formatter={(v, name) => [formatEuros(v), name]} contentStyle={{ fontSize: 12, borderRadius: 6 }} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
      </PieChart>
    </ResponsiveContainer>
  )
}
