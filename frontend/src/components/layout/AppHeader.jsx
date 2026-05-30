import { Space, Typography, Avatar, Dropdown, Button, Tag } from 'antd'
import {
  WalletOutlined,
  UserOutlined,
  LogoutOutlined,
  DownOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const { Text } = Typography

// Cabecera de la aplicación. Muestra el saldo del monedero del usuario,
// su nombre y un dropdown para cerrar sesión.
export default function AppHeader() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  if (!user) return null

  const formatearEuros = (n) =>
    new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(n ?? 0)

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const menuItems = [
    { key: 'profile', icon: <UserOutlined />, label: 'Mi perfil', disabled: true },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: 'Cerrar sesión', danger: true, onClick: handleLogout },
  ]

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', height: '100%', gap: 16 }}>
      {/* Pastilla con el saldo del monedero */}
      <Space style={{
        background: '#f0f7ff',
        padding: '6px 14px',
        borderRadius: 6,
        border: '1px solid #d6e4ff',
      }} size={6}>
        <WalletOutlined style={{ color: '#185FA5' }} />
        <Text strong style={{ color: '#185FA5' }}>{formatearEuros(user.saldo_monedero)}</Text>
      </Space>

      {/* Dropdown con avatar y nombre */}
      <Dropdown menu={{ items: menuItems }} placement="bottomRight" trigger={['click']}>
        <Button type="text" style={{ height: 'auto', padding: '4px 8px' }}>
          <Space size={8}>
            <Avatar size={28} style={{ background: '#185FA5' }}>
              {user.nombre_completo?.charAt(0).toUpperCase() || '?'}
            </Avatar>
            <span style={{ fontSize: 13 }}>{user.nombre_completo}</span>
            {user.rol === 'admin' && <Tag color="blue" style={{ margin: 0, fontSize: 10 }}>admin</Tag>}
            <DownOutlined style={{ fontSize: 10, color: '#999' }} />
          </Space>
        </Button>
      </Dropdown>
    </div>
  )
}
