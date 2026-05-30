import { useState, useEffect, useMemo } from 'react'
import { Card, Row, Col, Button, Table, Tag, Typography, Spin, Alert, App } from 'antd'
import { WalletOutlined, PlusOutlined } from '@ant-design/icons'
import { useAuth } from '../../context/AuthContext'
import * as monederoApi from '../../api/monedero'
import { formatEuros, formatFecha } from '../../utils/formatters'
import usePageTitle from '../../hooks/usePageTitle'

const { Title, Text, Paragraph } = Typography

// Mapeo de tipos de movimiento a etiqueta y color. Si el backend usa un
// valor no contemplado, se muestra el valor crudo con color neutro.
const TIPOS = {
  recarga:      { label: 'Recarga',      color: 'green'   },
  contratacion: { label: 'Contratación', color: 'volcano' },
  cancelacion:  { label: 'Devolución',   color: 'blue'    },
  devolucion:   { label: 'Devolución',   color: 'blue'    },
  ingreso:      { label: 'Ingreso',      color: 'green'   },
  cargo:        { label: 'Cargo',        color: 'volcano' },
}

// Vista del monedero virtual (RF-40 saldo, RF-46 recarga, RF-47 movimientos).
export default function Monedero() {
  usePageTitle('Monedero')
  const { user, refreshUser } = useAuth()
  const { message } = App.useApp()

  const [denominaciones, setDenominaciones] = useState([])
  const [movimientos, setMovimientos]       = useState([])
  const [seleccionada, setSeleccionada]     = useState(null)
  const [loading, setLoading]               = useState(true)
  const [recargando, setRecargando]         = useState(false)
  const [error, setError]                   = useState(null)

  const cargar = async () => {
    setLoading(true)
    setError(null)
    try {
      const [cantidades, movs] = await Promise.all([
        monederoApi.getCantidadesPermitidas(),
        monederoApi.getMovimientos(),
      ])
      // Las cantidades pueden venir como array de números/strings o envuelto.
      const rawDenoms = Array.isArray(cantidades)
        ? cantidades
        : (cantidades?.cantidades || cantidades?.items || [])
      setDenominaciones(
        rawDenoms.map(d => Number(typeof d === 'object' ? (d.valor ?? d.cantidad ?? d.monto) : d))
      )
      // Los movimientos pueden venir como array directo o envueltos.
      const lista = Array.isArray(movs)
        ? movs
        : (movs?.items || movs?.results || movs?.movimientos || [])
      setMovimientos(lista)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'No se pudo cargar el monedero')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { cargar() }, [])

  const handleRecargar = async () => {
    if (seleccionada == null) {
      message.warning('Selecciona una cantidad para recargar.')
      return
    }
    setRecargando(true)
    try {
      await monederoApi.recargar({ cantidad: seleccionada })
      message.success(`Has recargado ${formatEuros(seleccionada)} en tu monedero.`)
      setSeleccionada(null)
      await refreshUser()
      await cargar()
    } catch (err) {
      const detalle = err.response?.data?.detail
      message.error(typeof detalle === 'string' ? detalle : 'No se pudo completar la recarga.')
    } finally {
      setRecargando(false)
    }
  }

  // Orden defensivo: más reciente primero (RF-47).
  const movimientosOrdenados = useMemo(() => {
    return [...movimientos].sort((a, b) => new Date(b.fecha) - new Date(a.fecha))
  }, [movimientos])

  const columns = [
    {
      title: 'Fecha',
      dataIndex: 'fecha',
      key: 'fecha',
      render: (f) => formatFecha(f, 'DD MMM YYYY HH:mm'),
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo',
      key: 'tipo',
      render: (tipo) => {
        const cfg = TIPOS[tipo] || { label: tipo || '—', color: 'default' }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: 'Cantidad',
      dataIndex: 'monto',
      key: 'monto',
      align: 'right',
      render: (monto) => {
        const n = Number(monto)
        const positivo = n >= 0
        return (
          <Text strong style={{ color: positivo ? '#52c41a' : '#f5222d' }}>
            {positivo ? '+' : ''}{formatEuros(monto)}
          </Text>
        )
      },
    },
    {
      title: 'Saldo resultante',
      dataIndex: 'saldo_resultante',
      key: 'saldo_resultante',
      align: 'right',
      render: (s) => formatEuros(s),
    },
  ]

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>Monedero virtual</Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          Consulta tu saldo, recarga fondos y revisa el histórico de movimientos.
        </Paragraph>
      </div>

      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {/* Saldo disponible */}
        <Col xs={24} md={8}>
          <Card style={{ height: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <WalletOutlined style={{ color: '#185FA5', fontSize: 18 }} />
              <Text type="secondary">Saldo disponible</Text>
            </div>
            <div style={{ fontSize: 34, fontWeight: 600, color: '#185FA5', lineHeight: 1.2 }}>
              {formatEuros(user?.saldo_monedero)}
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Saldo ficticio para simular contrataciones.
            </Text>
          </Card>
        </Col>

        {/* Recarga */}
        <Col xs={24} md={16}>
          <Card title="Recargar monedero" style={{ height: '100%' }}>
            <Paragraph type="secondary" style={{ fontSize: 13, marginBottom: 16 }}>
              Selecciona una de las cantidades disponibles para añadir fondos.
            </Paragraph>
            <Row gutter={[12, 12]}>
              {denominaciones.map(d => (
                <Col key={d}>
                  <div
                    onClick={() => setSeleccionada(d)}
                    style={{
                      width: 110,
                      textAlign: 'center',
                      cursor: 'pointer',
                      padding: '16px 8px',
                      borderRadius: 8,
                      border: seleccionada === d ? '2px solid #185FA5' : '1px solid #f0f0f0',
                      background: seleccionada === d ? '#f0f7ff' : '#fff',
                      transition: 'all 0.15s',
                    }}
                  >
                    <Text strong style={{ fontSize: 16 }}>{formatEuros(d)}</Text>
                  </div>
                </Col>
              ))}
            </Row>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleRecargar}
              loading={recargando}
              disabled={seleccionada == null}
              style={{ marginTop: 16 }}
            >
              {seleccionada != null ? `Recargar ${formatEuros(seleccionada)}` : 'Recargar'}
            </Button>
          </Card>
        </Col>
      </Row>

      {/* Histórico de movimientos */}
      <Card title="Histórico de movimientos">
        {movimientosOrdenados.length === 0 ? (
          <Text type="secondary">Aún no hay movimientos en tu monedero.</Text>
        ) : (
          <Table
            rowKey="id"
            columns={columns}
            dataSource={movimientosOrdenados}
            pagination={{ pageSize: 10, hideOnSinglePage: true }}
            size="middle"
          />
        )}
      </Card>
    </div>
  )
}
