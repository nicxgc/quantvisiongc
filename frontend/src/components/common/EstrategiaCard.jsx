import { Card, Tag, Button, Typography, Space, Divider } from 'antd'
import { useNavigate } from 'react-router-dom'
import { CheckCircleFilled } from '@ant-design/icons'
import RiskIndicator from './RiskIndicator'
import {
  formatEuros,
  formatPorcentaje,
  formatPorcentajeConSigno,
  formatNumero,
} from '../../utils/formatters'

const { Title, Text } = Typography

// Tarjeta del catálogo (RF-17) con badge "Contratada" (RF-22).
// Las métricas resumen llegan planas en el objeto raíz con sufijo _oos.
export default function EstrategiaCard({ estrategia, contratada }) {
  const navigate = useNavigate()
  const esBenchmark = estrategia.tipo === 'benchmark'

  const retorno = estrategia.retorno_total_oos
  const sharpe  = estrategia.sharpe_oos
  const maxDD   = estrategia.mdd_oos

  return (
    <Card
      hoverable
      style={{ height: '100%' }}
      styles={{ body: { padding: 16, display: 'flex', flexDirection: 'column', height: '100%' } }}
      onClick={() => navigate(`/catalogo/${estrategia.id}`)}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <Tag color={esBenchmark ? 'default' : 'blue'} style={{ marginRight: 0 }}>
          {esBenchmark ? 'Benchmark' : 'Estrategia activa'}
        </Tag>
        {contratada && (
          <Tag icon={<CheckCircleFilled />} color="success" style={{ marginRight: 0 }}>
            Contratada
          </Tag>
        )}
      </div>

      <div style={{ marginBottom: 12 }}>
        <Title level={5} style={{ margin: 0, marginBottom: 2 }}>
          {estrategia.nombre || estrategia.codigo_estrategia || `Estrategia #${estrategia.id}`}
        </Title>
        <Text type="secondary" style={{ fontSize: 11, fontFamily: 'monospace' }}>
          {estrategia.codigo_estrategia}
        </Text>
      </div>

      <Space size={6} wrap style={{ marginBottom: 12 }}>
        {estrategia.categoria && <Tag style={{ fontSize: 10, marginRight: 0 }}>{estrategia.categoria}</Tag>}
        {estrategia.tipo_activo && <Tag style={{ fontSize: 10, marginRight: 0 }}>{estrategia.tipo_activo}</Tag>}
      </Space>

      <div style={{ marginBottom: 12 }}>
        <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>
          Riesgo (MiFID)
        </Text>
        <RiskIndicator nivel={estrategia.nivel_riesgo} />
      </div>

      <Divider style={{ margin: '8px 0' }} />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 12 }}>
        <Metric label="Retorno" valor={formatPorcentajeConSigno(retorno)} color={Number(retorno) >= 0 ? '#52c41a' : '#f5222d'} />
        <Metric label="Sharpe"  valor={formatNumero(sharpe)} />
        <Metric label="Max DD"  valor={formatPorcentaje(maxDD)} color="#f5222d" />
      </div>

      <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          {esBenchmark ? (
            <Text type="secondary" style={{ fontSize: 11 }}>Solo referencia</Text>
          ) : (
            <>
              <Text strong style={{ fontSize: 15 }}>{formatEuros(estrategia.precio_subscripcion)}</Text>
              <Text type="secondary" style={{ fontSize: 11 }}> /mes</Text>
            </>
          )}
        </div>
        <Button
          type="link"
          size="small"
          onClick={(e) => {
            e.stopPropagation()
            navigate(`/catalogo/${estrategia.id}`)
          }}
        >
          Ver detalle →
        </Button>
      </div>
    </Card>
  )
}

function Metric({ label, valor, color }) {
  return (
    <div>
      <Text type="secondary" style={{ fontSize: 10, display: 'block', textTransform: 'uppercase', letterSpacing: 0.5 }}>
        {label}
      </Text>
      <Text strong style={{ fontSize: 13, color: color || 'inherit' }}>
        {valor}
      </Text>
    </div>
  )
}
