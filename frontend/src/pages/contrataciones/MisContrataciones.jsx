import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Tag, Button, Typography, Spin, Alert, Empty, App } from 'antd'
import { useAuth } from '../../context/AuthContext'
import * as contratacionesApi from '../../api/contrataciones'
import * as estrategiasApi    from '../../api/estrategias'
import { formatEuros, formatFecha } from '../../utils/formatters'
import usePageTitle from '../../hooks/usePageTitle'

const { Title, Paragraph } = Typography

// Vista de las contrataciones del usuario (RF-44) con cancelación (RF-21).
// Como la respuesta puede no traer el nombre de la estrategia, se carga
// el catálogo en paralelo y se construye un mapa id -> nombre como respaldo.
export default function MisContrataciones() {
  usePageTitle('Mis contrataciones')
  const navigate = useNavigate()
  const { refreshUser } = useAuth()
  const { message, modal } = App.useApp()

  const [contrataciones, setContrataciones] = useState([])
  const [mapaNombres, setMapaNombres] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const cargar = async () => {
    setLoading(true)
    setError(null)
    try {
      const [contratos, catalogo] = await Promise.all([
        contratacionesApi.misContrataciones(),
        estrategiasApi.getCatalogo().catch(() => []),
      ])
      setContrataciones(Array.isArray(contratos) ? contratos : [])
      const mapa = {}
      ;(Array.isArray(catalogo) ? catalogo : []).forEach(e => {
        mapa[e.id] = e.nombre || e.codigo_estrategia
      })
      setMapaNombres(mapa)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'No se pudieron cargar las contrataciones')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { cargar() }, [])

  const nombreEstrategia = (c) =>
    c.nombre_estrategia || c.estrategia?.nombre || mapaNombres[c.id_estrategia] || `Estrategia #${c.id_estrategia}`

  const handleCancelar = (contrato) => {
    modal.confirm({
      title: 'Cancelar contratación',
      width: 420,
      content: (
        <div style={{ marginTop: 12 }}>
          <p>¿Seguro que quieres cancelar la contratación de <strong>{nombreEstrategia(contrato)}</strong>?</p>
          <p style={{ color: '#888', fontSize: 13 }}>
            Se devolverá <strong>{formatEuros(contrato.monto_invertido)}</strong> a tu monedero.
          </p>
        </div>
      ),
      okText: 'Sí, cancelar',
      okButtonProps: { danger: true },
      cancelText: 'No',
      onOk: async () => {
        try {
          await contratacionesApi.cancelar(contrato.id)
          message.success('Contratación cancelada. Importe devuelto al monedero.')
          await cargar()
          await refreshUser()
        } catch (err) {
          const detalle = err.response?.data?.detail
          message.error(typeof detalle === 'string' ? detalle : 'No se pudo cancelar la contratación.')
        }
      },
    })
  }

  // Orden por fecha de contratación descendente (RF-44).
  const datos = useMemo(() => {
    return [...contrataciones].sort(
      (a, b) => new Date(b.fecha_contratacion) - new Date(a.fecha_contratacion)
    )
  }, [contrataciones])

  const columns = [
    {
      title: 'Estrategia',
      key: 'estrategia',
      render: (_, c) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => navigate(`/catalogo/${c.id_estrategia}`)}>
          {nombreEstrategia(c)}
        </Button>
      ),
    },
    {
      title: 'Estado',
      dataIndex: 'estado',
      key: 'estado',
      render: (estado) => (
        <Tag color={estado === 'activa' ? 'success' : 'default'}>
          {estado === 'activa' ? 'Activa' : 'Cancelada'}
        </Tag>
      ),
      filters: [
        { text: 'Activa',    value: 'activa' },
        { text: 'Cancelada', value: 'cancelada' },
      ],
      onFilter: (value, c) => c.estado === value,
    },
    {
      title: 'Monto invertido',
      dataIndex: 'monto_invertido',
      key: 'monto_invertido',
      align: 'right',
      render: (m) => formatEuros(m),
    },
    {
      title: 'Fecha contratación',
      dataIndex: 'fecha_contratacion',
      key: 'fecha_contratacion',
      render: (f) => formatFecha(f, 'DD MMM YYYY'),
    },
    {
      title: 'Fecha cancelación',
      dataIndex: 'fecha_cancelacion',
      key: 'fecha_cancelacion',
      render: (f) => (f ? formatFecha(f, 'DD MMM YYYY') : '—'),
    },
    {
      title: 'Acción',
      key: 'accion',
      render: (_, c) =>
        c.estado === 'activa'
          ? <Button danger size="small" onClick={() => handleCancelar(c)}>Cancelar</Button>
          : null,
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>Mis contrataciones</Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          Consulta y gestiona las estrategias que has contratado.
        </Paragraph>
      </div>

      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
      ) : datos.length === 0 ? (
        <Empty description="Aún no has contratado ninguna estrategia" style={{ padding: 60 }}>
          <Button type="primary" onClick={() => navigate('/catalogo')}>Explorar catálogo</Button>
        </Empty>
      ) : (
        <Table
          rowKey="id"
          columns={columns}
          dataSource={datos}
          pagination={{ pageSize: 10, hideOnSinglePage: true }}
          size="middle"
          style={{ background: '#fff', borderRadius: 8 }}
        />
      )}
    </div>
  )
}
