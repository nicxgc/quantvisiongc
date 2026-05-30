import { Tooltip } from 'antd'

// Indicador de riesgo en escala 1-7 estilo MiFID (RF-19 detalle, RF-17 resumen).
// Verde 1-2 (bajo), amarillo 3-4 (medio), rojo 5-7 (alto).
// La inspiración visual viene del modelo de fichas de BBVA Asset Management
// citado en el capítulo 2 de la memoria.
export default function RiskIndicator({ nivel, mostrarTexto = true, tamano = 'normal' }) {
  if (nivel === null || nivel === undefined) {
    return <span style={{ color: '#999', fontSize: 12 }}>Riesgo no disponible</span>
  }

  const colorPorNivel = (n) => {
    if (n <= 2) return '#52c41a'
    if (n <= 4) return '#faad14'
    return '#f5222d'
  }

  const colorActivo = colorPorNivel(nivel)
  const anchoBarra  = tamano === 'grande' ? 16 : 12
  const altoBarra   = tamano === 'grande' ?  8 :  6

  return (
    <Tooltip title={`Nivel de riesgo ${nivel} de 7 (escala MiFID)`}>
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
        <div style={{ display: 'inline-flex', gap: 2 }}>
          {[1, 2, 3, 4, 5, 6, 7].map(n => (
            <div
              key={n}
              style={{
                width: anchoBarra,
                height: altoBarra,
                borderRadius: 1,
                background: n <= nivel ? colorActivo : '#f0f0f0',
                transition: 'background 0.2s',
              }}
            />
          ))}
        </div>
        {mostrarTexto && (
          <span style={{
            fontSize: tamano === 'grande' ? 13 : 11,
            fontWeight: 500,
            color: colorActivo,
          }}>
            {nivel}/7
          </span>
        )}
      </div>
    </Tooltip>
  )
}
