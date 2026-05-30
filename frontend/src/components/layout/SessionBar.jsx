import { Space, Typography } from 'antd'
import { SafetyCertificateOutlined, KeyOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import 'dayjs/locale/es'
import { useAuth } from '../../context/AuthContext'

dayjs.locale('es')

const { Text } = Typography

// Barra inferior de estado de sesión (RF-38). Indica conexión segura,
// token activo, nombre y rol del usuario, y fecha actual.
export default function SessionBar() {
  const { user } = useAuth()
  if (!user) return null

  const fecha = dayjs().format('DD MMM YYYY')

  return (
    <div style={{
      padding: '6px 24px',
      fontSize: 11,
      display: 'flex',
      justifyContent: 'flex-end',
      background: '#fafafa',
      borderTop: '1px solid #f0f0f0',
    }}>
      <Space split={<Text type="secondary">·</Text>} size={8}>
        <Space size={4}>
          <SafetyCertificateOutlined style={{ color: '#52c41a', fontSize: 12 }} />
          <Text type="secondary">Conexión segura</Text>
        </Space>
        <Space size={4}>
          <KeyOutlined style={{ color: '#185FA5', fontSize: 12 }} />
          <Text type="secondary">JWT activo</Text>
        </Space>
        <Text type="secondary">{user.nombre_completo} ({user.rol})</Text>
        <Text type="secondary">{fecha}</Text>
      </Space>
    </div>
  )
}
