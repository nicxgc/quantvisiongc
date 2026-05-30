// Paleta de colores para series multi-estrategia (gráficos superpuestos).
const PALETA = ['#185FA5', '#5DCAA5', '#FAAD14', '#F5222D', '#722ED1', '#13C2C2', '#EB2F96', '#FA8C16']

export function colorPorIndice(i) {
  return PALETA[i % PALETA.length]
}

// Fusiona las series temporales de varias estrategias en un único array
// apto para Recharts, donde cada estrategia es una clave por fecha.
//   entradas: [{ nombre, resultados: [{ fecha, equity, drawdown, periodo }] }]
//   campo: 'equity' | 'drawdown'
//   normalizarBase100: si true, cada serie se reescala para empezar en 100,
//     lo que permite comparar evoluciones relativas (RF-24 / RF-31).
// Devuelve: [{ fecha, [nombreA]: valor, [nombreB]: valor, ... }] ordenado por fecha.
export function fusionarSeries(entradas, periodo, campo, normalizarBase100 = false) {
  const mapaPorFecha = new Map()
  entradas.forEach(({ nombre, resultados }) => {
    const serie = (resultados || []).filter(r => r.periodo === periodo)
    const base = normalizarBase100 && serie.length > 0 ? Number(serie[0][campo]) : null
    serie.forEach(r => {
      if (!mapaPorFecha.has(r.fecha)) mapaPorFecha.set(r.fecha, { fecha: r.fecha })
      let valor = Number(r[campo])
      if (normalizarBase100 && base) valor = (valor / base) * 100
      mapaPorFecha.get(r.fecha)[nombre] = valor
    })
  })
  return Array.from(mapaPorFecha.values()).sort((a, b) => new Date(a.fecha) - new Date(b.fecha))
}
