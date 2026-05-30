import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import AppRoutes from './routes'

// App es ahora solo el punto de montaje de los tres proveedores globales:
// BrowserRouter (navegación), AuthProvider (sesión) y AppRoutes (árbol de vistas).
// ConfigProvider de Ant Design ya está en main.jsx, más arriba en el árbol.
function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
