import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import dayjs from 'dayjs'
import { formatEuros, formatFecha } from '../../utils/formatters'

// Curva de equity (RF-19). Recibe datos ya filtrados por periodo y con
// valores numéricos. Optimizado para miles de puntos: sin animación,
// sin puntos individuales (RNF-10).
export default function EquityChart({ data, alto = 300 }) {
  if (!Array.isArray(data) || data.length === 0) {
    return <SinDatos alto={alto} />
  }

  return (
    <ResponsiveContainer width="100%" height={alto}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
        <XAxis
          dataKey="fecha"
          tick={{ fontSize: 11, fill: '#999' }}
          tickFormatter={(f) => dayjs(f).format('MMM YY')}
          minTickGap={48}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: '#999' }}
          tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
          tickLine={false}
          axisLine={false}
          domain={['auto', 'auto']}
          width={48}
        />
        <Tooltip
          formatter={(v) => [formatEuros(v), 'Equity']}
          labelFormatter={(f) => formatFecha(f, 'DD MMM YYYY')}
          contentStyle={{ fontSize: 12, borderRadius: 6 }}
        />
        <Line
          type="monotone"
          dataKey="equity"
          stroke="#185FA5"
          strokeWidth={1.8}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

function SinDatos({ alto }) {
  return (
    <div style={{ height: alto, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999', fontSize: 13 }}>
      Sin datos para este periodo
    </div>
  )
}
