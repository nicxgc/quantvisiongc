import { LineChart, Line, ResponsiveContainer } from 'recharts'

// Mini gráfico de tendencia sin ejes ni tooltip, para usar dentro de listas
// y tablas (RF-25 ranking con indicador visual de tendencia).
export default function Sparkline({ data, dataKey = 'valor', color = '#185FA5', alto = 28 }) {
  if (!Array.isArray(data) || data.length === 0) {
    return <div style={{ height: alto }} />
  }
  return (
    <ResponsiveContainer width="100%" height={alto}>
      <LineChart data={data}>
        <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={1.3} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
