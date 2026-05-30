import { Layout } from 'antd'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import AppHeader from './AppHeader'
import SessionBar from './SessionBar'

const { Sider, Header, Content, Footer } = Layout

// Chasis principal de la aplicación. Envuelve todas las rutas protegidas
// con sidebar, header, footer de sesión y un área central para las vistas.
export default function AppShell() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={220}
        theme="light"
        style={{
          borderRight: '1px solid #f0f0f0',
          background: '#fff',
        }}
      >
        <Sidebar />
      </Sider>

      <Layout>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          borderBottom: '1px solid #f0f0f0',
          height: 56,
          lineHeight: 'normal',
        }}>
          <AppHeader />
        </Header>

        <Content style={{ padding: 24, background: '#f5f5f5' }}>
          <Outlet />
        </Content>

        <Footer style={{ padding: 0, background: 'transparent' }}>
          <SessionBar />
        </Footer>
      </Layout>
    </Layout>
  )
}
