import { Navigate, Outlet } from 'react-router-dom'
import { Spin } from 'antd'
import { useAuth } from '../../context/AuthContext'

// Protege rutas exclusivas del administrador.
// Si no hay sesión → /login. Si hay sesión pero no es admin → /dashboard.
export default function AdminRoute() {
  const { isAuthenticated, isAdmin, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />
  return isAdmin ? <Outlet /> : <Navigate to="/dashboard" replace />
}
