import { Routes, Route, Navigate } from 'react-router-dom'
import PrivateRoute from './components/layout/PrivateRoute'
import AdminRoute  from './components/layout/AdminRoute'
import AppShell    from './components/layout/AppShell'
import Login       from './pages/auth/Login'
import Register    from './pages/auth/Register'
import Catalogo    from './pages/catalogo/Catalogo'
import Detalle     from './pages/catalogo/Detalle'
import MisContrataciones from './pages/contrataciones/MisContrataciones'
import Monedero    from './pages/monedero/Monedero'
import Dashboard   from './pages/dashboard/Dashboard'
import Comparador  from './pages/comparador/Comparador'
import Admin       from './pages/admin/Admin'
import NotFound    from './pages/NotFound'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login"    element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route element={<PrivateRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/dashboard" replace />} />

          <Route path="/dashboard"      element={<Dashboard />} />
          <Route path="/catalogo"       element={<Catalogo />} />
          <Route path="/catalogo/:id"   element={<Detalle />} />
          <Route path="/comparador"     element={<Comparador />} />
          <Route path="/contrataciones" element={<MisContrataciones />} />
          <Route path="/monedero"       element={<Monedero />} />

          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<Admin />} />
          </Route>

          {/* 404 dentro de la zona autenticada */}
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>

      {/* URLs no autenticadas que no son /login ni /register: a login */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
