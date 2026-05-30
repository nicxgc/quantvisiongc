import { useState, useEffect, useMemo } from 'react'
import {
  Card, Row, Col, Typography, Spin, Alert, Timeline, Empty, Tabs, DatePicker,
  Button, List, Drawer,
} from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, WalletOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import * as dashboardApi      from '../../api/dashboard'
import * as contratacionesApi from '../../api/contrataciones'
import * as estrategiasApi    from '../../api/estrategias'
import {
  formatEuros, formatPorcentaje, formatPorcentajeConSigno,
  formatNumero, formatFechaRelativa,
} from '../../utils/formatters'
import { fusionarSeries, colorPorIndice } from '../../utils/series'
import EquityMultiChart   from '../../components/charts/EquityMultiChart'
import DrawdownMultiChart from '../../components/charts/DrawdownMultiChart'
import EquityChart        from '../../components/charts/EquityChart'
import Sparkline          from '../../components/charts/Sparkline'
import DistribucionPie    from '../../components/charts/DistribucionPie'
import usePageTitle from '../../hooks/usePageTitle'

const { Title, Text, Paragraph } = Typography
const { RangePicker } = DatePicker

const PERIODO = 'oos'

export default function Dashboard() {
  usePageTitle('Dashboard')
  const navigate = useNavigate()

  const [kpis, setKpis]           = useState(null)
  const [actividad, setActividad] = useState([])
  const [cartera, setCartera]     = useState([]) // [{ estrategia, resultados, montoInvertido }]
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [rango, setRango]         = useState(null)

  const [seleccionada, setSeleccionada]   = useState(null)
  const [drawerAbierto, setDrawerAbierto] = useState(false)

  useEffect(() => {
    const cargar = async () => {
      setLoading(true)
      setError(null)
      try {
        const [kpisData, actividadData, contratos] = await Promise.all([
          dashboardApi.getKPIs(),
          dashboardApi.getActividadReciente(),
          contratacionesApi.misContrataciones().catch(() => []),
        ])
        setKpis(kpisData)
        setActividad(Array.isArray(actividadData) ? actividadData : [])

        const activas = (Array.isArray(contratos) ? contratos : []).filter(c => c.estado === 'activa')

        // Importe invertido acumulado por estrategia (para la distribución).
        const montoPorEstrategia = {}
        activas.forEach(c => {
          montoPorEstrategia[c.id_estrategia] = (montoPorEstrategia[c.id_estrategia] || 0) + Number(c.monto_invertido)
        })

        const idsUnicos = [...new Set(activas.map(c => c.id_estrategia))]

        const carteraData = await Promise.all(
          idsUnicos.map(async (idEst) => {
            const [estrategia, resultados] = await Promise.all([
              estrategiasApi.getDetalle(idEst),
              estrategiasApi.getResultados(idEst),
            ])
            return {
              estrategia,
              resultados: Array.isArray(resultados) ? resultados : [],
              montoInvertido: montoPorEstrategia[idEst] || 0,
            }
          })
        )
        setCartera(carteraData)
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'No se pudo cargar el dashboard')
      } finally {
        setLoading(false)
      }
    }
    cargar()
  }, [])

  const series = useMemo(
    () => cartera.map((item, i) => ({
      key: item.estrategia.nombre || item.estrategia.codigo_estrategia,
      color: colorPorIndice(i),
    })),
    [cartera]
  )

  const entradas = useMemo(
    () => cartera.map(item => ({
      nombre: item.estrategia.nombre || item.estrategia.codigo_estrategia,
      resultados: item.resultados,
    })),
    [cartera]
  )

  const equityFull   = useMemo(() => fusionarSeries(entradas, PERIODO, 'equity', true), [entradas])
  const drawdownFull = useMemo(() => fusionarSeries(entradas, PERIODO, 'drawdown', false), [entradas])

  const rangoDisponible = useMemo(() => {
    if (equityFull.length === 0) return null
    return [dayjs(equityFull[0].fecha), dayjs(equityFull[equityFull.length - 1].fecha)]
  }, [equityFull])

  useEffect(() => {
    if (rangoDisponible && !rango) setRango(rangoDisponible)
  }, [rangoDisponible, rango])

  const recortar = (data) => {
    if (!rango || rango.length !== 2) return data
    const [ini, fin] = rango
    return data.filter(d => {
      const f = dayjs(d.fecha)
      return !f.isBefore(ini, 'day') && !f.isAfter(fin, 'day')
    })
  }

  const equityData   = useMemo(() => recortar(equityFull),   [equityFull, rango])
  const drawdownData = useMemo(() => recortar(drawdownFull), [drawdownFull, rango])

  // Ranking por retorno out-of-sample (RF-25).
  const ranking = useMemo(() => {
    return cartera
      .map((item, i) => {
        const oosMetrica    = (item.estrategia.metricas || []).find(m => m.periodo === PERIODO)
        const oosResultados = item.resultados.filter(r => r.periodo === PERIODO)
        return {
          id: item.estrategia.id,
          nombre: item.estrategia.nombre || item.estrategia.codigo_estrategia,
          categoria: item.estrategia.categoria,
          color: colorPorIndice(i),
          retorno: oosMetrica ? Number(oosMetrica.retorno_total) : null,
          metricas: oosMetrica,
          equitySerie: oosResultados.map(r => ({ fecha: r.fecha, equity: Number(r.equity) })),
          montoInvertido: item.montoInvertido,
        }
      })
      .sort((a, b) => (b.retorno ?? -Infinity) - (a.retorno ?? -Infinity))
  }, [cartera])

  // Distribución por categoría ponderada por importe invertido (RF-26).
  const distribucion = useMemo(() => {
    const porCategoria = {}
    cartera.forEach(item => {
      const cat = item.estrategia.categoria || 'Sin categoría'
      porCategoria[cat] = (porCategoria[cat] || 0) + (item.montoInvertido || 0)
    })
    return Object.entries(porCategoria).map(([categoria, valor], i) => ({
      name: categoria,
      value: valor,
      color: colorPorIndice(i),
    }))
  }, [cartera])

  const abrirDetalle = (item) => {
    setSeleccionada(item)
    setDrawerAbierto(true)
  }

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
  }

  const pnl  = Number(kpis?.pnl_absoluto)
  const rent = Number(kpis?.rentabilidad_total)
  const tieneCartera = cartera.length > 0

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>Dashboard</Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          Resumen de tu cartera de estrategias y actividad reciente.
        </Paragraph>
      </div>

      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}

      {/* KPIs (RF-23) */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <KpiCard titulo="Saldo disponible"    valor={formatEuros(kpis?.saldo_monedero)}   color="#185FA5" icono={<WalletOutlined />} />
        <KpiCard titulo="Total invertido"     valor={formatEuros(kpis?.total_invertido)} />
        <KpiCard titulo="Valor actual"        valor={formatEuros(kpis?.valor_actual)} />
        <KpiCard titulo="P&L"                 valor={formatEuros(kpis?.pnl_absoluto)} color={pnl >= 0 ? '#52c41a' : '#f5222d'} icono={pnl >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />} />
        <KpiCard titulo="Rentabilidad"        valor={formatPorcentajeConSigno(kpis?.rentabilidad_total)} color={rent >= 0 ? '#52c41a' : '#f5222d'} />
        <KpiCard titulo="Estrategias activas" valor={kpis?.num_estrategias_activas ?? 0} />
      </Row>

      {/* Rendimiento de la cartera + actividad reciente */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={16}>
          <Card
            title="Rendimiento de la cartera"
            style={{ minHeight: 420 }}
            extra={
              tieneCartera && rangoDisponible ? (
                <RangePicker
                  value={rango}
                  onChange={(r) => setRango(r && r.length === 2 ? r : rangoDisponible)}
                  allowClear={false}
                  size="small"
                  format="DD/MM/YYYY"
                  disabledDate={(current) =>
                    current && (current < rangoDisponible[0].startOf('day') || current > rangoDisponible[1].endOf('day'))
                  }
                />
              ) : null
            }
          >
            {!tieneCartera ? (
              <Empty description="Contrata estrategias para ver el rendimiento de tu cartera" style={{ padding: 40 }}>
                <Button type="primary" onClick={() => navigate('/catalogo')}>Explorar catálogo</Button>
              </Empty>
            ) : (
              <Tabs
                items={[
                  { key: 'equity',   label: 'Equity (base 100)', children: <EquityMultiChart data={equityData} series={series} base100 /> },
                  { key: 'drawdown', label: 'Drawdown',          children: <DrawdownMultiChart data={drawdownData} series={series} /> },
                ]}
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="Actividad reciente" style={{ minHeight: 420 }}>
            {actividad.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Sin actividad reciente" />
            ) : (
              <Timeline
                items={actividad.map((ev, idx) => {
                  const esContratacion = ev.tipo === 'contratacion'
                  return {
                    key: idx,
                    color: esContratacion ? 'blue' : 'green',
                    children: (
                      <div>
                        <Text strong style={{ fontSize: 13 }}>
                          {esContratacion ? 'Contrataste' : 'Cancelaste'} {ev.nombre_estrategia}
                        </Text>
                        <div style={{ fontSize: 12, fontWeight: 500, color: esContratacion ? '#f5222d' : '#52c41a' }}>
                          {esContratacion ? '−' : '+'}{formatEuros(ev.monto)}
                        </div>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {formatFechaRelativa(ev.fecha)}
                        </Text>
                      </div>
                    ),
                  }
                })}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* Ranking + distribución */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Ranking por retorno (out-of-sample)" style={{ minHeight: 340 }}>
            {ranking.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Sin estrategias en cartera" />
            ) : (
              <List
                dataSource={ranking}
                renderItem={(item, idx) => (
                  <List.Item style={{ cursor: 'pointer', padding: '10px 4px' }} onClick={() => abrirDetalle(item)}>
                    <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: 12 }}>
                      <Text type="secondary" style={{ width: 18, textAlign: 'right' }}>{idx + 1}</Text>
                      <span style={{ width: 10, height: 10, borderRadius: '50%', background: item.color, flexShrink: 0 }} />
                      <Text strong style={{ flex: 1, fontSize: 13 }} ellipsis={{ tooltip: item.nombre }}>{item.nombre}</Text>
                      <div style={{ width: 70, flexShrink: 0 }}>
                        <Sparkline data={item.equitySerie} dataKey="equity" color={item.color} />
                      </div>
                      <Text strong style={{ width: 72, textAlign: 'right', color: Number(item.retorno) >= 0 ? '#52c41a' : '#f5222d' }}>
                        {formatPorcentajeConSigno(item.retorno)}
                      </Text>
                    </div>
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Distribución de la cartera por categoría" style={{ minHeight: 340 }}>
            {distribucion.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Sin estrategias en cartera" />
            ) : (
              <DistribucionPie data={distribucion} />
            )}
          </Card>
        </Col>
      </Row>

      {/* Detalle rápido (RF-29) */}
      <Drawer
        title={seleccionada?.nombre}
        open={drawerAbierto}
        onClose={() => setDrawerAbierto(false)}
        width={440}
      >
        {seleccionada && (
          <div>
            <Row gutter={[12, 12]}>
              <MiniKpi label="Retorno"     valor={formatPorcentajeConSigno(seleccionada.metricas?.retorno_total)} color={Number(seleccionada.metricas?.retorno_total) >= 0 ? '#52c41a' : '#f5222d'} />
              <MiniKpi label="Sharpe"      valor={formatNumero(seleccionada.metricas?.sharpe)} />
              <MiniKpi label="Max DD"      valor={formatPorcentaje(seleccionada.metricas?.mdd)} color="#f5222d" />
              <MiniKpi label="Volatilidad" valor={formatPorcentaje(seleccionada.metricas?.volatility)} />
            </Row>

            <div style={{ marginTop: 20 }}>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
                Evolución del equity (out-of-sample)
              </Text>
              <EquityChart data={seleccionada.equitySerie} alto={180} />
            </div>

            <div style={{ marginTop: 16, color: '#888', fontSize: 13 }}>
              Importe invertido: <strong>{formatEuros(seleccionada.montoInvertido)}</strong>
            </div>

            <Button type="primary" block style={{ marginTop: 20 }} onClick={() => navigate(`/catalogo/${seleccionada.id}`)}>
              Ver detalle completo
            </Button>
          </div>
        )}
      </Drawer>
    </div>
  )
}

function KpiCard({ titulo, valor, color, icono }) {
  return (
    <Col xs={12} sm={8} lg={4}>
      <Card size="small" styles={{ body: { padding: 14 } }}>
        <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 6 }}>
          {icono && <span style={{ marginRight: 4 }}>{icono}</span>}{titulo}
        </Text>
        <Text strong style={{ fontSize: 18, color: color || 'inherit' }}>{valor}</Text>
      </Card>
    </Col>
  )
}

function MiniKpi({ label, valor, color }) {
  return (
    <Col span={12}>
      <div style={{ background: '#fafafa', borderRadius: 6, padding: 10 }}>
        <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 2 }}>{label}</Text>
        <Text strong style={{ fontSize: 15, color: color || 'inherit' }}>{valor}</Text>
      </div>
    </Col>
  )
}
