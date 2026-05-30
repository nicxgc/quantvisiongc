import { Tabs, Typography } from 'antd'
import { UserOutlined, DatabaseOutlined, CloudUploadOutlined } from '@ant-design/icons'
import GestionUsuarios    from './GestionUsuarios'
import GestionEstrategias from './GestionEstrategias'
import IngestaPaquete     from './IngestaPaquete'
import usePageTitle from '../../hooks/usePageTitle'

const { Title, Paragraph } = Typography

// Panel de administración del sistema (acceso restringido por AdminRoute).
export default function Admin() {
  usePageTitle('Panel de administración')
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>Panel de administración</Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          Gestión de usuarios, estrategias e ingesta de datos.
        </Paragraph>
      </div>

      <Tabs
        defaultActiveKey="usuarios"
        items={[
          { key: 'usuarios',    label: <span><UserOutlined /> Usuarios</span>,                   children: <GestionUsuarios /> },
          { key: 'estrategias', label: <span><DatabaseOutlined /> Estrategias</span>,            children: <GestionEstrategias /> },
          { key: 'ingesta',     label: <span><CloudUploadOutlined /> Ingesta de paquetes</span>, children: <IngestaPaquete /> },
        ]}
      />
    </div>
  )
}
