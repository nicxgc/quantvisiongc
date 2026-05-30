import { Navigate, Outlet } from 'react-router-dom'
import { Spin } from 'antd'
import { useAuth } from '../../context/AuthContext'

// Protege rutas que requieren sesión activa.
// Muestra un spinner mientras AuthContext verifica el token inicial,
// redirige a /login si no hay sesión, o renderiza la vista hija si sí la hay.
export default function PrivateRoute() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />
}
