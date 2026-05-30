import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  Legend, Tooltip, ResponsiveContainer,
} from 'recharts'

// Ejes del radar: 6 dimensiones de perfil riesgo/rendimiento (RF-33).
// `invertir` = true para métricas donde un valor menor es mejor (volatilidad).
// Para mdd no se invierte: al ser valor negativo, max(mdd) es el menos negativo = mejor.
const EJES = [
  { key: 'retorno',    label: 'Retorno',          invertir: false },
  { key: 'sharpe',     label: 'Sharpe',           invertir: false },
  { key: 'sortino',    label: 'Sortino',          invertir: false },
  { key: 'hit_rate',   label: 'Win rate',         invertir: false },
  { key: 'volatility', label: 'Baja volatilidad', invertir: true  },
  { key: 'mdd',        label: 'Control drawdown', invertir: false },
]

// Normaliza los valores de un eje al rango 0-100 (min-max relativo al grupo).
// Valores nulos puntúan 0 (muesca visible en el polígono, p.ej. hit_rate del buy & hold).
function normalizarEje(filas, key, invertir) {
  const map = new Map()
  const validos = filas.filter(f => f[key] != null && !isNaN(f[key]))
  if (validos.length === 0) {
    filas.forEach(f => map.set(f.id, 0))
    return map
  }
  const vals = validos.map(f => f[key])
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const range = max - min
  filas.forEach(f => {
    const v = f[key]
    if (v == null || isNaN(v)) { map.set(f.id, 0); return }
    if (range === 0)           { map.set(f.id, 100); return }
    let norm = ((v - min) / range) * 100
    if (invertir) norm = 100 - norm
    map.set(f.id, norm)
  })
  return map
}

export default function PerfilRadar({ filas, series, alto = 360 }) {
  if (filas.length < 2) {
    return (
      <div style={{ height: alto, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999', fontSize: 13, textAlign: 'center', padding: 24 }}>
        Selecciona al menos 2 estrategias para comparar perfiles.
      </div>
    )
  }

  const normales = {}
  EJES.forEach(e => { normales[e.key] = normalizarEje(filas, e.key, e.invertir) })

  const data = EJES.map(e => {
    const row = { axis: e.label }
    series.forEach(s => {
      const fila = filas.find(f => f.nombre === s.key)
      if (fila) row[s.key] = Math.round(normales[e.key].get(fila.id) ?? 0)
    })
    return row
  })

  return (
    <ResponsiveContainer width="100%" height={alto}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke="#e8e8e8" />
        <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11, fill: '#666' }} />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        {series.map(s => (
          <Radar
            key={s.key}
            name={s.key}
            dataKey={s.key}
            stroke={s.color}
            fill={s.color}
            fillOpacity={0.15}
            strokeWidth={1.5}
          />
        ))}
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Tooltip formatter={(v) => `${v} / 100`} contentStyle={{ fontSize: 12, borderRadius: 6 }} />
      </RadarChart>
    </ResponsiveContainer>
  )
}
