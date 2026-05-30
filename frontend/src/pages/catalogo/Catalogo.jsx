import { useState, useEffect, useMemo } from 'react'
import { Row, Col, Input, Select, Space, Typography, Spin, Empty, Alert } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import * as estrategiasApi    from '../../api/estrategias'
import * as contratacionesApi from '../../api/contrataciones'
import EstrategiaCard from '../../components/common/EstrategiaCard'
import usePageTitle from '../../hooks/usePageTitle'

const { Title, Paragraph } = Typography

// Vista del catálogo público (RF-17). El backend solo devuelve estrategias
// activas (los benchmarks viven en el comparador), por eso no hay filtro
// de tipo: únicamente buscador y ordenación (RF-18).
export default function Catalogo() {
  usePageTitle('Catálogo')
  const [estrategias, setEstrategias] = useState([])
  const [idsContratadas, setIdsContratadas] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [busqueda, setBusqueda]     = useState('')
  const [ordenarPor, setOrdenarPor] = useState('nombre_asc')

  useEffect(() => {
    const cargar = async () => {
      setLoading(true)
      setError(null)
      try {
        const [catalogo, contrataciones] = await Promise.all([
          estrategiasApi.getCatalogo(),
          contratacionesApi.misContrataciones().catch(() => []),
        ])
        setEstrategias(Array.isArray(catalogo) ? catalogo : [])
        const ids = new Set(
          (Array.isArray(contrataciones) ? contrataciones : [])
            .filter(c => c.estado === 'activa')
            .map(c => c.id_estrategia)
        )
        setIdsContratadas(ids)
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'No se pudieron cargar las estrategias')
      } finally {
        setLoading(false)
      }
    }
    cargar()
  }, [])

  const estrategiasVisibles = useMemo(() => {
    let lista = [...estrategias]

    if (busqueda.trim()) {
      const q = busqueda.toLowerCase().trim()
      lista = lista.filter(e =>
        (e.nombre || '').toLowerCase().includes(q) ||
        (e.codigo_estrategia || '').toLowerCase().includes(q)
      )
    }

    // Las métricas vienen como strings; coercionamos antes de comparar.
    const num = (v) => (v === null || v === undefined || v === '' || isNaN(Number(v)) ? null : Number(v))
    const comparadores = {
      nombre_asc:   (a, b) => (a.nombre || a.codigo_estrategia || '').localeCompare(b.nombre || b.codigo_estrategia || ''),
      nombre_desc:  (a, b) => (b.nombre || b.codigo_estrategia || '').localeCompare(a.nombre || a.codigo_estrategia || ''),
      retorno_desc: (a, b) => (num(b.retorno_total_oos) ?? -Infinity) - (num(a.retorno_total_oos) ?? -Infinity),
      retorno_asc:  (a, b) => (num(a.retorno_total_oos) ??  Infinity) - (num(b.retorno_total_oos) ??  Infinity),
      sharpe_desc:  (a, b) => (num(b.sharpe_oos) ?? -Infinity) - (num(a.sharpe_oos) ?? -Infinity),
      riesgo_asc:   (a, b) => (a.nivel_riesgo ?? 99) - (b.nivel_riesgo ?? 99),
      riesgo_desc:  (a, b) => (b.nivel_riesgo ?? -1) - (a.nivel_riesgo ?? -1),
      precio_asc:   (a, b) => (num(a.precio_subscripcion) ?? Infinity) - (num(b.precio_subscripcion) ?? Infinity),
    }
    lista.sort(comparadores[ordenarPor] || comparadores.nombre_asc)
    return lista
  }, [estrategias, busqueda, ordenarPor])

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>Catálogo de estrategias</Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          Explora las estrategias disponibles y consulta su rendimiento histórico fuera de muestra.
        </Paragraph>
      </div>

      <div style={{ background: '#fff', padding: 16, borderRadius: 8, marginBottom: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
        <Space size="middle" wrap style={{ width: '100%' }}>
          <Input
            placeholder="Buscar por nombre o código…"
            prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            style={{ width: 280 }}
            allowClear
          />
          <Select
            value={ordenarPor}
            onChange={setOrdenarPor}
            style={{ width: 220 }}
            options={[
              { value: 'nombre_asc',   label: 'Nombre (A → Z)' },
              { value: 'nombre_desc',  label: 'Nombre (Z → A)' },
              { value: 'retorno_desc', label: 'Mayor retorno' },
              { value: 'retorno_asc',  label: 'Menor retorno' },
              { value: 'sharpe_desc',  label: 'Mejor Sharpe' },
              { value: 'riesgo_asc',   label: 'Menor riesgo' },
              { value: 'riesgo_desc',  label: 'Mayor riesgo' },
              { value: 'precio_asc',   label: 'Menor precio' },
            ]}
          />
        </Space>
      </div>

      {error && (
        <Alert type="error" message="Error al cargar el catálogo" description={error} showIcon style={{ marginBottom: 16 }} />
      )}

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
        </div>
      )}

      {!loading && !error && estrategiasVisibles.length === 0 && (
        <Empty description={busqueda ? 'No hay estrategias que cumplan los criterios' : 'No hay estrategias disponibles'} />
      )}

      {!loading && estrategiasVisibles.length > 0 && (
        <Row gutter={[16, 16]}>
          {estrategiasVisibles.map(e => (
            <Col xs={24} sm={12} lg={8} xxl={6} key={e.id}>
              <EstrategiaCard
                estrategia={e}
                contratada={idsContratadas.has(e.id)}
              />
            </Col>
          ))}
        </Row>
      )}
    </div>
  )
}
