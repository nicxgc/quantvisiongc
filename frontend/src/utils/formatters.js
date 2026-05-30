import dayjs from 'dayjs'
import 'dayjs/locale/es'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)
dayjs.locale('es')

// Convierte a número de forma segura. El backend serializa los campos
// Decimal como strings ("9.99", "-0.0234"), así que hay que coercionarlos
// antes de operar. Devuelve null si el valor es ausente o no numérico.
const aNumero = (n) => {
  if (n === null || n === undefined || n === '') return null
  const num = Number(n)
  return isNaN(num) ? null : num
}

export const formatEuros = (n) => {
  const num = aNumero(n)
  if (num === null) return '—'
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
  }).format(num)
}

// Asume ratio decimal (0.15 = 15%).
export const formatPorcentaje = (n, decimales = 2) => {
  const num = aNumero(n)
  if (num === null) return '—'
  return `${(num * 100).toFixed(decimales)}%`
}

// Igual que el anterior pero con '+' delante si es positivo.
export const formatPorcentajeConSigno = (n, decimales = 2) => {
  const num = aNumero(n)
  if (num === null) return '—'
  const valor = num * 100
  const signo = valor > 0 ? '+' : ''
  return `${signo}${valor.toFixed(decimales)}%`
}

// Para Sharpe, Sortino, Calmar (números adimensionales).
export const formatNumero = (n, decimales = 2) => {
  const num = aNumero(n)
  if (num === null) return '—'
  return num.toFixed(decimales)
}

export const formatFecha = (fecha, formato = 'DD MMM YYYY') => {
  if (!fecha) return '—'
  return dayjs(fecha).format(formato)
}

// Tiempo relativo en español: "hace 2 horas", "hace 3 días".
export const formatFechaRelativa = (fecha) => {
  if (!fecha) return '—'
  return dayjs(fecha).fromNow()
}
