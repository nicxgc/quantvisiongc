import { Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  AppstoreOutlined,
  LineChartOutlined,
  FileTextOutlined,
  WalletOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useAuth } from '../../context/AuthContext'

// Sidebar de navegación principal. Lee el rol del usuario para decidir
// si muestra la sección Admin. El item activo se calcula a partir de
// la ruta actual con useLocation.
export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAdmin } = useAuth()

  const itemsPrincipales = [
    { key: '/dashboard',      icon: <DashboardOutlined />, label: 'Dashboard' },
    { key: '/catalogo',       icon: <AppstoreOutlined />,  label: 'Estrategias' },
    { key: '/comparador',     icon: <LineChartOutlined />, label: 'Comparador' },
    { key: '/contrataciones', icon: <FileTextOutlined />,  label: 'Mis contrataciones' },
    { key: '/monedero',       icon: <WalletOutlined />,    label: 'Monedero' },
  ]

  const itemsAdmin = [
    { key: '/admin', icon: <SettingOutlined />, label: 'Panel admin' },
  ]

  const items = [
    { type: 'group', label: 'Principal',      children: itemsPrincipales },
    ...(isAdmin ? [{ type: 'group', label: 'Administración', children: itemsAdmin }] : []),
  ]

  // Calcular la clave seleccionada: el item cuyo path es prefijo de la ruta actual.
  const todosLosItems = [...itemsPrincipales, ...(isAdmin ? itemsAdmin : [])]
  const selectedItem  = todosLosItems.find(item => location.pathname.startsWith(item.key))
  const selectedKey   = selectedItem ? [selectedItem.key] : []

  return (
    <div>
      {/* Cabecera del sidebar con el logo de la plataforma */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}>
        <div style={{
          width: 28, height: 28,
          background: '#185FA5',
          borderRadius: 6,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 16L10 8L14 12L19 5"
              stroke="#fff" strokeWidth="2.2"
              strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <span style={{ fontSize: 15, fontWeight: 600 }}>QuantVisionGC</span>
      </div>

      <Menu
        mode="inline"
        items={items}
        selectedKeys={selectedKey}
        onClick={({ key }) => navigate(key)}
        style={{ borderRight: 0, paddingTop: 8 }}
      />
    </div>
  )
}
