import { useState, useEffect, useMemo } from 'react'
import {
  Card, Select, Typography, Spin, Alert, Empty, Tabs, Segmented,
  Table, Tag, Space, Row, Col, InputNumber,
} from 'antd'
import { CheckCircleFilled } from '@ant-design/icons'
import dayjs from 'dayjs'
import * as estrategiasApi from '../../api/estrategias'
import {
  formatEuros, formatPorcentaje, formatPorcentajeConSigno, formatNumero,
} from '../../utils/formatters'
import { fusionarSeries, colorPorIndice } from '../../utils/series'
import EquityMultiChart   from '../../components/charts/EquityMultiChart'
import DrawdownMultiChart from '../../components/charts/DrawdownMultiChart'
import PerfilRadar        from '../../components/charts/PerfilRadar'
import usePageTitle from '../../hooks/usePageTitle'

const { Title, Text, Paragraph } = Typography
const MAX_SELECCION = 5

const aplicarRango = (data, rango) => {
  if (rango === 'todo' || data.length === 0) return data
  const meses = { '3m': 3, '6m': 6, '1a': 12 }[rango]
  if (!meses) return data
  const ultima = dayjs(data[data.length - 1].fecha)
  const desde  = ultima.subtract(meses, 'month')
  return data.filter(d => !dayjs(d.fecha).isBefore(desde, 'day'))
}

const idExtremo = (filas, key, modo) => {
  const validos = filas.filter(x => x[key] !== null && x[key] !== undefined && !isNaN(x[key]))
  if (validos.length === 0) return null
  return validos.reduce(
    (a, b) => (modo === 'max' ? (a[key] >= b[key] ? a : b) : (a[key] <= b[key] ? a : b))
  ).id
}

export default function Comparador() {
  usePageTitle('Comparador')
  const [disponibles, setDisponibles]     = useState([])
  const [seleccionadas, setSeleccionadas] = useState([])
  const [cacheDatos, setCacheDatos]       = useState({})
  const [loadingDisp, setLoadingDisp]     = useState(true)
  const [fetchingSel, setFetchingSel]     = useState(false)
  const [error, setError]                 = useState(null)
  const [rango, setRango]                 = useState('todo')
  const [monto, setMonto]                 = useState(1000)
  const [periodo, setPeriodo]             = useState('oos')

  useEffect(() => {
    const cargar = async () => {
      setLoadingDisp(true)
      setError(null)
      try {
        const lista = await estrategiasApi.getCatalogo({ incluir_benchmarks: true })
        setDisponibles(Array.isArray(lista) ? lista : [])
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'No se pudieron cargar las estrategias')
      } finally {
        setLoadingDisp(false)
      }
    }
    cargar()
  }, [])

  useEffect(() => {
    const fetchPendientes = async () => {
      const pendientes = seleccionadas.filter(id => !cacheDatos[id])
      if (pendientes.length === 0) return
      setFetchingSel(true)
      try {
        const nuevos = await Promise.all(
          pendientes.map(async (id) => {
            const [estrategia, resultados] = await Promise.all([
              estrategiasApi.getDetalle(id),
              estrategiasApi.getResultados(id),
            ])
            return [id, { estrategia, resultados: Array.isArray(resultados) ? resultados : [] }]
          })
        )
        setCacheDatos(prev => ({ ...prev, ...Object.fromEntries(nuevos) }))
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'No se pudo cargar el detalle')
      } finally {
        setFetchingSel(false)
      }
    }
    fetchPendientes()
  }, [seleccionadas]) // eslint-disable-line react-hooks/exhaustive-deps

  const datosSel = useMemo(
    () => seleccionadas.map(id => cacheDatos[id]).filter(Boolean),
    [seleccionadas, cacheDatos]
  )

  const colorPorId = useMemo(() => {
    const m = {}
    seleccionadas.forEach((id, i) => { m[id] = colorPorIndice(i) })
    return m
  }, [seleccionadas])

  const series = useMemo(
    () => datosSel.map(item => ({
      key: item.estrategia.nombre || item.estrategia.codigo_estrategia,
      color: colorPorId[item.estrategia.id],
    })),
    [datosSel, colorPorId]
  )

  const entradas = useMemo(
    () => datosSel.map(item => ({
      nombre: item.estrategia.nombre || item.estrategia.codigo_estrategia,
      resultados: item.resultados,
    })),
    [datosSel]
  )

  const equityFull   = useMemo(() => fusionarSeries(entradas, periodo, 'equity', true), [entradas, periodo])
  const drawdownFull = useMemo(() => fusionarSeries(entradas, periodo, 'drawdown', false), [entradas, periodo])

  const equityData   = useMemo(() => aplicarRango(equityFull, rango),   [equityFull, rango])
  const drawdownData = useMemo(() => aplicarRango(drawdownFull, rango), [drawdownFull, rango])

  const filas = useMemo(() => {
    return datosSel.map(item => {
      const oos = (item.estrategia.metricas || []).find(m => m.periodo === periodo)
      const num = (v) => (v === null || v === undefined || v === '' ? null : Number(v))
      return {
        id: item.estrategia.id,
        nombre: item.estrategia.nombre || item.estrategia.codigo_estrategia,
        tipo: item.estrategia.tipo,
        retorno:    oos ? num(oos.retorno_total) : null,
        sharpe:     oos ? num(oos.sharpe) : null,
        volatility: oos ? num(oos.volatility) : null,
        mdd:        oos ? num(oos.mdd) : null,
        hit_rate:   oos ? num(oos.hit_rate) : null,
        sortino:    oos ? num(oos.sortino) : null,
        n_trades:   oos?.n_trades ?? null,
        precio:     num(item.estrategia.precio_subscripcion),
      }
    })
  }, [datosSel, periodo])

  const mejor = useMemo(() => ({
    retorno:    idExtremo(filas, 'retorno',    'max'),
    sharpe:     idExtremo(filas, 'sharpe',     'max'),
    volatility: idExtremo(filas, 'volatility', 'min'),
    mdd:        idExtremo(filas, 'mdd',        'max'),
    hit_rate:   idExtremo(filas, 'hit_rate',   'max'),
    sortino:    idExtremo(filas, 'sortino',    'max'),
    precio:     idExtremo(filas.filter(f => f.tipo !== 'benchmark'), 'precio', 'min'),
  }), [filas])

  // Simulación de inversión (RF-34): respeta el rango temporal seleccionado.
  const simulacion = useMemo(() => {
    return datosSel.map(item => {
      const fila = filas.find(f => f.id === item.estrategia.id) || { id: item.estrategia.id, nombre: '', tipo: '' }
      const oosRes = item.resultados.filter(r => r.periodo === periodo)
      if (oosRes.length < 2) return { ...fila, sin_datos: true }

      let res = oosRes
      if (rango !== 'todo') {
        const meses  = { '3m': 3, '6m': 6, '1a': 12 }[rango]
        const ultima = dayjs(oosRes[oosRes.length - 1].fecha)
        const desde  = ultima.subtract(meses, 'month')
        res = oosRes.filter(r => !dayjs(r.fecha).isBefore(desde, 'day'))
      }
      if (res.length < 2) return { ...fila, sin_datos: true }

      const eqIni = Number(res[0].equity)
      const eqFin = Number(res[res.length - 1].equity)
      if (!eqIni || isNaN(eqIni) || isNaN(eqFin)) return { ...fila, sin_datos: true }

      const factor        = eqFin / eqIni
      const valorBruto    = monto * factor
      const gananciaBruta = valorBruto - monto
      const comisionPct   = (Number(item.estrategia.comision_ganancias) || 0) / 100
      const comision      = Math.max(0, gananciaBruta) * comisionPct
      const gananciaNeta  = gananciaBruta - comision
      const valorNeto     = monto + gananciaNeta
      const rentabilidadNeta = gananciaNeta / monto

      return { ...fila, valorNeto, gananciaNeta, comision, rentabilidadNeta }
    })
  }, [datosSel, filas, monto, rango, periodo])

  const renderMetrica = (key, formatter) => (_, row) => {
    const v = row[key]
    const txt = v === null || v === undefined ? '—' : formatter(v)
    const esMejor = row.id === mejor[key]
    return (
      <span style={{ fontWeight: esMejor ? 600 : 400, color: esMejor ? '#52c41a' : 'inherit' }}>
        {esMejor && <CheckCircleFilled style={{ marginRight: 4, fontSize: 11 }} />}
        {txt}
      </span>
    )
  }

  const columns = [
    {
      title: 'Estrategia',
      key: 'nombre',
      fixed: 'left',
      width: 240,
      render: (_, row) => (
        <Space size={8}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: colorPorId[row.id], flexShrink: 0 }} />
          <Text strong style={{ fontSize: 13 }}>{row.nombre}</Text>
          {row.tipo === 'benchmark' && <Tag color="default" style={{ fontSize: 10, marginLeft: 4 }}>Benchmark</Tag>}
        </Space>
      ),
    },
    { title: 'Retorno',     key: 'retorno',    align: 'right', render: renderMetrica('retorno',    formatPorcentajeConSigno) },
    { title: 'Sharpe',      key: 'sharpe',     align: 'right', render: renderMetrica('sharpe',     formatNumero) },
    { title: 'Volatilidad', key: 'volatility', align: 'right', render: renderMetrica('volatility', formatPorcentaje) },
    { title: 'Max DD',      key: 'mdd',        align: 'right', render: renderMetrica('mdd',        formatPorcentaje) },
    { title: 'Win rate',    key: 'hit_rate',   align: 'right', render: renderMetrica('hit_rate',   formatPorcentaje) },
    { title: 'Sortino',     key: 'sortino',    align: 'right', render: renderMetrica('sortino',    formatNumero) },
    { title: 'Nº ops', dataIndex: 'n_trades', key: 'n_trades', align: 'right', render: (v) => v ?? '—' },
    {
      title: 'Precio',
      key: 'precio',
      align: 'right',
      render: (_, row) => {
        if (row.tipo === 'benchmark') return <Text type="secondary">Gratis</Text>
        const esMejor = row.id === mejor.precio
        return (
          <span style={{ fontWeight: esMejor ? 600 : 400, color: esMejor ? '#52c41a' : 'inherit' }}>
            {esMejor && <CheckCircleFilled style={{ marginRight: 4, fontSize: 11 }} />}
            {formatEuros(row.precio)}
          </span>
        )
      },
    },
  ]

  const columnasSimulacion = [
    {
      title: 'Estrategia',
      key: 'nombre',
      render: (_, row) => (
        <Space size={6}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: colorPorId[row.id], flexShrink: 0 }} />
          <Text style={{ fontSize: 13 }}>{row.nombre}</Text>
        </Space>
      ),
    },
    {
      title: 'Valor final',
      dataIndex: 'valorNeto',
      align: 'right',
      render: (v, row) => row.sin_datos ? '—' : <Text strong>{formatEuros(v)}</Text>,
    },
    {
      title: 'Ganancia',
      dataIndex: 'gananciaNeta',
      align: 'right',
      render: (v, row) => {
        if (row.sin_datos) return '—'
        const pos = v >= 0
        return <Text strong style={{ color: pos ? '#52c41a' : '#f5222d' }}>{pos ? '+' : ''}{formatEuros(v)}</Text>
      },
    },
    {
      title: 'Comisión',
      dataIndex: 'comision',
      align: 'right',
      render: (v, row) => row.sin_datos ? '—' : formatEuros(v),
    },
    {
      title: 'Rent. neta',
      dataIndex: 'rentabilidadNeta',
      align: 'right',
      render: (v, row) => {
        if (row.sin_datos) return '—'
        const pos = v >= 0
        return <Text style={{ color: pos ? '#52c41a' : '#f5222d' }}>{formatPorcentajeConSigno(v)}</Text>
      },
    },
  ]

  const opcionesSelector = useMemo(
    () => disponibles.map(e => ({
      value: e.id,
      label: e.nombre || e.codigo_estrategia,
      tipo: e.tipo,
    })),
    [disponibles]
  )

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>Comparador de estrategias</Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          Selecciona hasta {MAX_SELECCION} estrategias (incluidos benchmarks) para compararlas en paralelo.
        </Paragraph>
      </div>

      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}

      <Card style={{ marginBottom: 16 }}>
        <Select
          mode="multiple"
          value={seleccionadas}
          onChange={(vals) => setSeleccionadas(vals.slice(0, MAX_SELECCION))}
          placeholder={loadingDisp ? 'Cargando estrategias…' : `Selecciona hasta ${MAX_SELECCION} estrategias`}
          style={{ width: '100%' }}
          maxTagCount="responsive"
          loading={loadingDisp}
          showSearch
          optionFilterProp="label"
          options={opcionesSelector}
          optionRender={(option) => (
            <Space>
              <span>{option.data.label}</span>
              {option.data.tipo === 'benchmark' && <Tag color="default" style={{ fontSize: 10, marginLeft: 4 }}>Benchmark</Tag>}
            </Space>
          )}
        />
        <Text type="secondary" style={{ fontSize: 12, marginTop: 8, display: 'block' }}>
          {seleccionadas.length} de {MAX_SELECCION} seleccionadas
          {fetchingSel && <> · <Spin size="small" style={{ marginLeft: 8 }} /></>}
        </Text>
      </Card>

      {seleccionadas.length === 0 ? (
        <Card>
          <Empty description="Selecciona estrategias arriba para comenzar la comparación" style={{ padding: 40 }} />
        </Card>
      ) : (
        <>
          {/* Toggle de periodo de análisis: OOS por defecto, dev opcional */}
          <Card style={{ marginBottom: 16 }} styles={{ body: { padding: '12px 16px' } }}>
            <Space wrap>
              <Text strong>Periodo de análisis:</Text>
              <Segmented
                value={periodo}
                onChange={setPeriodo}
                options={[
                  { label: 'Out-of-sample', value: 'oos' },
                  { label: 'Desarrollo',    value: 'dev' },
                ]}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {periodo === 'oos'
                  ? 'Datos no usados en el entrenamiento (validación real)'
                  : 'Datos del periodo de desarrollo de la estrategia'}
              </Text>
            </Space>
          </Card>

          <Card
            title={`Rendimiento comparado (${periodo === 'oos' ? 'out-of-sample' : 'desarrollo'})`}
            style={{ marginBottom: 16 }}
            extra={
              <Segmented
                value={rango}
                onChange={setRango}
                size="small"
                options={[
                  { label: 'Todo',    value: 'todo' },
                  { label: '3 meses', value: '3m' },
                  { label: '6 meses', value: '6m' },
                  { label: '1 año',   value: '1a' },
                ]}
              />
            }
          >
            <Tabs
              items={[
                { key: 'equity',   label: 'Equity (base 100)', children: <EquityMultiChart   data={equityData}   series={series} base100 /> },
                { key: 'drawdown', label: 'Drawdown',          children: <DrawdownMultiChart data={drawdownData} series={series} /> },
              ]}
            />
          </Card>

          <Card title="Tabla comparativa" style={{ marginBottom: 16 }}>
            <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 12 }}>
              El icono verde indica el mejor valor de cada métrica. Los benchmarks quedan excluidos de la comparación de precio.
            </Paragraph>
            <Table
              rowKey="id"
              columns={columns}
              dataSource={filas}
              pagination={false}
              size="middle"
              scroll={{ x: 'max-content' }}
            />
          </Card>

          {/* Radar (RF-33) + Simulación (RF-34) */}
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card
                title="Perfil riesgo/rendimiento"
                extra={<Text type="secondary" style={{ fontSize: 11 }}>Periodo {periodo === 'oos' ? 'OOS' : 'desarrollo'} completo</Text>}
              >
                <PerfilRadar filas={filas} series={series} />
                <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
                  Cada eje se normaliza 0-100 dentro del grupo seleccionado (100 = mejor valor relativo).
                  Para Volatilidad, valores menores puntúan más alto. Un eje con valor 0 indica que la estrategia
                  no aplica esa métrica (p.ej. win rate en un buy &amp; hold).
                </Text>
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card
                title="Simulación de inversión"
                extra={
                  <Space>
                    <Text type="secondary" style={{ fontSize: 12 }}>Monto inicial:</Text>
                    <InputNumber
                      value={monto}
                      onChange={(v) => setMonto(typeof v === 'number' && v > 0 ? v : 1000)}
                      min={1}
                      step={100}
                      addonAfter="€"
                      style={{ width: 140 }}
                      size="small"
                    />
                  </Space>
                }
              >
                <Table
                  rowKey="id"
                  size="small"
                  pagination={false}
                  columns={columnasSimulacion}
                  dataSource={simulacion}
                />
                <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
                  Calculado sobre el rango temporal seleccionado. La comisión sobre ganancias se aplica según cada estrategia
                  (0 % para benchmarks).
                </Text>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  )
}
