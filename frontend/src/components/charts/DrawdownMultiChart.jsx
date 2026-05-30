import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import dayjs from 'dayjs'
import { formatPorcentaje, formatFecha } from '../../utils/formatters'

// Gráfico multi-línea de drawdown (RF-28 dashboard, RF-32 comparador).
// Líneas en vez de áreas para que varias estrategias no se tapen entre sí.
export default function DrawdownMultiChart({ data, series, alto = 260 }) {
  if (!Array.isArray(data) || data.length === 0 || series.length === 0) {
    return <SinDatos alto={alto} />
  }
  return (
    <ResponsiveContainer width="100%" height={alto}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
        <XAxis dataKey="fecha" tickFormatter={(f) => dayjs(f).format('MMM YY')} minTickGap={48} tick={{ fontSize: 11, fill: '#999' }} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#999' }} tickLine={false} axisLine={false} width={44} tickFormatter={(v) => formatPorcentaje(v, 0)} />
        <Tooltip
          formatter={(v, name) => [formatPorcentaje(v), name]}
          labelFormatter={(f) => formatFecha(f, 'DD MMM YYYY')}
          contentStyle={{ fontSize: 12, borderRadius: 6 }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {series.map(s => (
          <Line key={s.key} type="monotone" dataKey={s.key} stroke={s.color} strokeWidth={1.4} dot={false} isAnimationActive={false} connectNulls />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

function SinDatos({ alto }) {
  return (
    <div style={{ height: alto, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999', fontSize: 13 }}>
      Sin datos para mostrar
    </div>
  )
}
