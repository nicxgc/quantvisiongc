import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card, Row, Col, Typography, Tag, Button, Segmented, Spin, Alert,
  Descriptions, Space, App, Switch,
} from 'antd'
import { ArrowLeftOutlined, CheckCircleFilled } from '@ant-design/icons'
import * as estrategiasApi    from '../../api/estrategias'
import * as contratacionesApi from '../../api/contrataciones'
import { useAuth } from '../../context/AuthContext'
import RiskIndicator from '../../components/common/RiskIndicator'
import EquityChart   from '../../components/charts/EquityChart'
import DrawdownChart from '../../components/charts/DrawdownChart'
import {
  formatEuros, formatPorcentaje, formatPorcentajeConSigno,
  formatNumero, formatFecha,
} from '../../utils/formatters'
import { fusionarSeries, colorPorIndice } from '../../utils/series'
import EquityMultiChart   from '../../components/charts/EquityMultiChart'
import DrawdownMultiChart from '../../components/charts/DrawdownMultiChart'
import usePageTitle from '../../hooks/usePageTitle'

const { Title, Text, Paragraph } = Typography

// Vista de detalle de una estrategia (RF-19).
// Las métricas llegan en estrategia.metricas (array con un objeto por
// periodo). Los resultados temporales en un endpoint aparte, también
// con todos los periodos juntos, filtrados aquí en el frontend.
export default function Detalle() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, refreshUser } = useAuth()
  const { message, modal } = App.useApp()

  const [estrategia, setEstrategia] = useState(null)
  const [resultados, setResultados] = useState([])
  const [contratada, setContratada] = useState(false)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [periodo, setPeriodo]       = useState('oos')

  const [mostrarBenchmarks, setMostrarBenchmarks] = useState(false)
  const [benchmarksDatos, setBenchmarksDatos]     = useState(null)
  const [cargandoBenchmarks, setCargandoBenchmarks] = useState(false)

  usePageTitle(estrategia ? `${estrategia.nombre} · Estrategia` : 'Estrategia')

  useEffect(() => {
    const cargar = async () => {
      setLoading(true)
      setError(null)
      try {
        const [detalle, datos, contrataciones] = await Promise.all([
          estrategiasApi.getDetalle(id),
          estrategiasApi.getResultados(id),
          contratacionesApi.misContrataciones().catch(() => []),
        ])
        setEstrategia(detalle)
        setResultados(Array.isArray(datos) ? datos : [])
        const activa = (Array.isArray(contrataciones) ? contrataciones : [])
          .some(c => c.estado === 'activa' && c.id_estrategia === Number(id))
        setContratada(activa)
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'No se pudo cargar la estrategia')
      } finally {
        setLoading(false)
      }
    }
    cargar()
  }, [id])

  const periodosDisponibles = useMemo(
    () => new Set(resultados.map(r => r.periodo)),
    [resultados]
  )

  useEffect(() => {
    if (resultados.length > 0 && !periodosDisponibles.has('oos') && periodosDisponibles.has('dev')) {
      setPeriodo('dev')
    }
  }, [resultados, periodosDisponibles])

  useEffect(() => {
    if (!mostrarBenchmarks || benchmarksDatos !== null || !estrategia) return
    const cargarBenchmarks = async () => {
      setCargandoBenchmarks(true)
      try {
        const catalogo = await estrategiasApi.getCatalogo({ incluir_benchmarks: true })
        // Identifica el subyacente desde el codigo_estrategia.
        // Convención de naming: "TICKER_resto_del_codigo" (p.ej. "AAPL_arima_garch" -> "AAPL").
        const prefijoActivo = (estrategia.codigo_estrategia || '').split('_')[0]
        const relevantes = (Array.isArray(catalogo) ? catalogo : []).filter(
          b => b.tipo === 'benchmark'
            && b.tipo_activo === estrategia.tipo_activo
            && (b.codigo_estrategia || '').split('_')[0] === prefijoActivo
        )
        const datos = await Promise.all(
          relevantes.map(async (b) => {
            const res = await estrategiasApi.getResultados(b.id)
            return { estrategia: b, resultados: Array.isArray(res) ? res : [] }
          })
        )
        setBenchmarksDatos(datos)
      } catch (err) {
        console.error('No se pudieron cargar los benchmarks', err)
        setBenchmarksDatos([])
      } finally {
        setCargandoBenchmarks(false)
      }
    }
    cargarBenchmarks()
  }, [mostrarBenchmarks, benchmarksDatos, estrategia])

  const datosGrafico = useMemo(() => {
    return resultados
      .filter(r => r.periodo === periodo)
      .map(r => ({
        fecha: r.fecha,
        equity: Number(r.equity),
        drawdown: Number(r.drawdown),
        retorno: Number(r.retorno),
      }))
  }, [resultados, periodo])

  const entradasMulti = useMemo(() => {
    const lista = [{ nombre: estrategia?.nombre || estrategia?.codigo_estrategia || 'Estrategia', resultados }]
    if (mostrarBenchmarks && Array.isArray(benchmarksDatos)) {
      benchmarksDatos.forEach(b => {
        lista.push({
          nombre: b.estrategia.nombre || b.estrategia.codigo_estrategia,
          resultados: b.resultados,
        })
      })
    }
    return lista
  }, [estrategia, resultados, mostrarBenchmarks, benchmarksDatos])

  const seriesMulti = useMemo(
    () => entradasMulti.map((e, i) => ({
      key: e.nombre,
      color: i === 0 ? '#185FA5' : colorPorIndice(i),
    })),
    [entradasMulti]
  )

  const equityMulti   = useMemo(() => fusionarSeries(entradasMulti, periodo, 'equity', true),   [entradasMulti, periodo])
  const drawdownMulti = useMemo(() => fusionarSeries(entradasMulti, periodo, 'drawdown', false), [entradasMulti, periodo])

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
  }

  if (error) {
    return (
      <div>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/catalogo')} style={{ marginBottom: 16 }}>
          Volver al catálogo
        </Button>
        <Alert type="error" message="Error" description={error} showIcon />
      </div>
    )
  }

  if (!estrategia) return null

  const esBenchmark = estrategia.tipo === 'benchmark'

  // Las métricas vienen en un array estrategia.metricas, con un objeto por
  // periodo (dev/oos) y los nombres SIN sufijo (sharpe, mdd, retorno_total...).
  // Se localiza el objeto del periodo seleccionado y se leen sus campos.
  const metricasPeriodo = (estrategia.metricas || []).find(m => m.periodo === periodo) || null
  const metrica = (nombre) => metricasPeriodo?.[nombre]

  const handleContratar = () => {
    const precio    = Number(estrategia.precio_subscripcion)
    const saldo     = Number(user?.saldo_monedero)
    const saldoTras = saldo - precio
    const sinSaldo  = saldoTras < 0

    modal.confirm({
      title: 'Confirmar contratación',
      width: 440,
      content: (
        <div style={{ marginTop: 12 }}>
          <p style={{ marginBottom: 12 }}>
            Vas a contratar <strong>{estrategia.nombre || estrategia.codigo_estrategia}</strong>.
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
            <span style={{ color: '#888' }}>Precio de suscripción</span>
            <strong>{formatEuros(precio)}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
            <span style={{ color: '#888' }}>Saldo actual</span>
            <span>{formatEuros(saldo)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderTop: '1px solid #f0f0f0', marginTop: 4, paddingTop: 8 }}>
            <span style={{ color: '#888' }}>Saldo tras contratar</span>
            <strong style={{ color: sinSaldo ? '#f5222d' : 'inherit' }}>{formatEuros(saldoTras)}</strong>
          </div>
          {sinSaldo && (
            <Alert
              type="warning"
              showIcon
              style={{ marginTop: 12 }}
              message="Saldo insuficiente"
              description="Recarga tu monedero antes de contratar esta estrategia."
            />
          )}
        </div>
      ),
      okText: 'Contratar',
      okButtonProps: { disabled: sinSaldo },
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await contratacionesApi.crear({ id_estrategia: Number(id) })
          message.success('Estrategia contratada correctamente.')
          setContratada(true)
          await refreshUser()
        } catch (err) {
          const detalle = err.response?.data?.detail
          message.error(typeof detalle === 'string' ? detalle : 'No se pudo completar la contratación.')
        }
      },
    })
  }

  return (
    <div>
      <Button
        icon={<ArrowLeftOutlined />}
        type="text"
        onClick={() => navigate('/catalogo')}
        style={{ marginBottom: 12, paddingLeft: 0 }}
      >
        Volver al catálogo
      </Button>

      {/* Cabecera */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <Space size={8} style={{ marginBottom: 8 }} wrap>
              <Tag color={esBenchmark ? 'default' : 'blue'}>{esBenchmark ? 'Benchmark' : 'Estrategia activa'}</Tag>
              {contratada && <Tag icon={<CheckCircleFilled />} color="success">Contratada</Tag>}
              {estrategia.estado && <Tag color={estrategia.estado === 'activa' ? 'green' : 'orange'}>{estrategia.estado}</Tag>}
            </Space>
            <Title level={3} style={{ margin: 0 }}>
              {estrategia.nombre || estrategia.codigo_estrategia}
            </Title>
            <Text type="secondary" style={{ fontFamily: 'monospace', fontSize: 12 }}>
              {estrategia.codigo_estrategia}
            </Text>
            <div style={{ marginTop: 8 }}>
              <Space size={6} wrap>
                {estrategia.categoria && <Tag>{estrategia.categoria}</Tag>}
                {estrategia.tipo_activo && <Tag>{estrategia.tipo_activo}</Tag>}
              </Space>
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            {!esBenchmark && (
              <div style={{ marginBottom: 8 }}>
                <Text strong style={{ fontSize: 22 }}>{formatEuros(estrategia.precio_subscripcion)}</Text>
                <Text type="secondary"> /mes</Text>
              </div>
            )}
            {esBenchmark ? (
              <Text type="secondary" style={{ fontSize: 12 }}>
                Los benchmarks no son contratables.<br />Solo sirven de referencia en el comparador.
              </Text>
            ) : contratada ? (
              <Button type="default" disabled>Ya contratada</Button>
            ) : (
              <Button type="primary" size="large" onClick={handleContratar}>Contratar</Button>
            )}
          </div>
        </div>
      </Card>

      {/* Selector de periodo */}
      <div style={{ marginBottom: 16 }}>
        <Segmented
          value={periodo}
          onChange={setPeriodo}
          options={[
            { label: 'Out-of-sample', value: 'oos', disabled: !periodosDisponibles.has('oos') },
            { label: 'Desarrollo',    value: 'dev', disabled: !periodosDisponibles.has('dev') },
          ]}
        />
        <Text type="secondary" style={{ marginLeft: 12, fontSize: 12 }}>
          {periodo === 'oos'
            ? 'Resultados fuera de muestra (datos no usados en el entrenamiento)'
            : 'Resultados del periodo de desarrollo (datos de entrenamiento)'}
          {metricasPeriodo?.fecha_inicio_periodo && (
            <> · {formatFecha(metricasPeriodo.fecha_inicio_periodo)} — {formatFecha(metricasPeriodo.fecha_fin_periodo)}</>
          )}
        </Text>
      </div>

      {/* KPIs del periodo seleccionado */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <KpiCard titulo="Retorno total"  valor={formatPorcentajeConSigno(metrica('retorno_total'))} color={Number(metrica('retorno_total')) >= 0 ? '#52c41a' : '#f5222d'} />
        <KpiCard titulo="Sharpe"         valor={formatNumero(metrica('sharpe'))} />
        <KpiCard titulo="Sortino"        valor={formatNumero(metrica('sortino'))} />
        <KpiCard titulo="Calmar"         valor={formatNumero(metrica('calmar'))} />
        <KpiCard titulo="Max drawdown"   valor={formatPorcentaje(metrica('mdd'))} color="#f5222d" />
        <KpiCard titulo="Volatilidad"    valor={formatPorcentaje(metrica('volatility'))} />
        <KpiCard titulo="CAGR"           valor={formatPorcentajeConSigno(metrica('cagr'))} color={Number(metrica('cagr')) >= 0 ? '#52c41a' : '#f5222d'} />
        <KpiCard titulo="Hit rate"       valor={formatPorcentaje(metrica('hit_rate'))} />
        <KpiCard titulo="Nº operaciones" valor={metrica('n_trades') ?? '—'} />
        <KpiCard titulo="Profit factor"  valor={formatNumero(metrica('profit_factor'))} />
      </Row>

      {/* Toggle benchmarks */}
      <Space style={{ marginBottom: 12 }}>
        <Switch
          size="small"
          checked={mostrarBenchmarks}
          onChange={setMostrarBenchmarks}
          loading={cargandoBenchmarks}
        />
        <Text style={{ fontSize: 13 }}>
          Mostrar benchmarks {(() => {
            const prefijo = (estrategia?.codigo_estrategia || '').split('_')[0]
            return prefijo ? `de ${prefijo}` : ''
          })()}
        </Text>
      </Space>

      {/* Gráfico de equity */}
      <Card title="Curva de equity" size="small" style={{ marginBottom: 16 }}>
        {mostrarBenchmarks
          ? <EquityMultiChart   data={equityMulti}   series={seriesMulti} base100 alto={300} />
          : <EquityChart        data={datosGrafico}  alto={300} />}
      </Card>

      {/* Gráfico de drawdown */}
      <Card title="Drawdown" size="small" style={{ marginBottom: 16 }}>
        {mostrarBenchmarks
          ? <DrawdownMultiChart data={drawdownMulti} series={seriesMulti} alto={260} />
          : <DrawdownChart      data={datosGrafico}  alto={260} />}
      </Card>

      {/* Información + riesgo */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="Información" size="small" style={{ height: '100%' }}>
            {estrategia.descripcion && (
              <Paragraph style={{ fontSize: 13 }}>{estrategia.descripcion}</Paragraph>
            )}
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Periodo de datos">
                {formatFecha(estrategia.fecha_inicio)} — {formatFecha(estrategia.fecha_fin)}
              </Descriptions.Item>
              {!esBenchmark && (
                <Descriptions.Item label="Precio de suscripción">
                  {formatEuros(estrategia.precio_subscripcion)} /mes
                </Descriptions.Item>
              )}
              {!esBenchmark && (
                <Descriptions.Item label="Comisión sobre ganancias">
                  {formatPorcentaje(Number(estrategia.comision_ganancias) / 100)}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="Tipo de activo">{estrategia.tipo_activo || '—'}</Descriptions.Item>
              <Descriptions.Item label="Categoría">{estrategia.categoria || '—'}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="Nivel de riesgo" size="small" style={{ height: '100%' }}>
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <RiskIndicator nivel={estrategia.nivel_riesgo} tamano="grande" />
              <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 16 }}>
                Escala MiFID de 1 (menor riesgo) a 7 (mayor riesgo)
              </Paragraph>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

function KpiCard({ titulo, valor, color }) {
  return (
    <Col xs={12} sm={8} lg={6}>
      <Card size="small" styles={{ body: { padding: 12 } }}>
        <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>{titulo}</Text>
        <Text strong style={{ fontSize: 16, color: color || 'inherit' }}>{valor}</Text>
      </Card>
    </Col>
  )
}
