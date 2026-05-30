import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import dayjs from 'dayjs'
import { formatPorcentaje, formatFecha } from '../../utils/formatters'

// Gráfico de drawdown (RF-19, RF-28). Área roja con degradado.
// Datos ya filtrados por periodo y numéricos. Sin animación (RNF-10).
export default function DrawdownChart({ data, alto = 220 }) {
  if (!Array.isArray(data) || data.length === 0) {
    return <SinDatos alto={alto} />
  }

  return (
    <ResponsiveContainer width="100%" height={alto}>
      <AreaChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
        <defs>
          <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#f5222d" stopOpacity={0.35} />
            <stop offset="95%" stopColor="#f5222d" stopOpacity={0.03} />
          </linearGradient>
        </defs>
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
          tickFormatter={(v) => formatPorcentaje(v, 0)}
          tickLine={false}
          axisLine={false}
          width={48}
        />
        <Tooltip
          formatter={(v) => [formatPorcentaje(v), 'Drawdown']}
          labelFormatter={(f) => formatFecha(f, 'DD MMM YYYY')}
          contentStyle={{ fontSize: 12, borderRadius: 6 }}
        />
        <Area
          type="monotone"
          dataKey="drawdown"
          stroke="#f5222d"
          strokeWidth={1.3}
          fill="url(#ddGradient)"
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
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
