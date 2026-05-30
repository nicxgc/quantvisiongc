import { Card } from 'antd'

// Wrapper común para las páginas de autenticación (login y registro).
// Centra una Card en pantalla con la sombra y el ancho que se le indique.
export default function AuthLayout({ children, width = 420 }) {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#f5f5f5',
      padding: 20,
    }}>
      <Card style={{
        width,
        boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
      }}>
        {children}
      </Card>
    </div>
  )
}
