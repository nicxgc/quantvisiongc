import { useState, useEffect } from 'react'
import { Form, Input, Button, Typography, Alert, Space } from 'antd'
import { MailOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import AuthLayout from '../../components/layout/AuthLayout'
import usePageTitle from '../../hooks/usePageTitle'

const { Title, Text } = Typography

// Página de inicio de sesión (RF-03).
// Si el usuario ya está autenticado, redirige automáticamente a /dashboard.
export default function Login() {
  usePageTitle('Iniciar sesión')
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [errorGeneral, setErrorGeneral] = useState(null)

  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard', { replace: true })
  }, [isAuthenticated, navigate])

  const onFinish = async ({ correo, password }) => {
    setLoading(true)
    setErrorGeneral(null)
    try {
      await login(correo, password)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const status = err.response?.status
      const data   = err.response?.data

      if (status === 401) {
        // Credenciales incorrectas: mensaje general sin pista de qué campo está mal,
        // para no facilitar enumeración de cuentas existentes.
        setErrorGeneral('Credenciales incorrectas. Verifica tu correo y contraseña.')
      } else if (status === 422 && Array.isArray(data?.detail)) {
        // Errores de validación Pydantic mapeados a sus campos.
        const fields = data.detail
          .map(e => ({ name: e.loc?.[e.loc.length - 1], errors: [e.msg] }))
          .filter(f => f.name)
        form.setFields(fields)
      } else {
        setErrorGeneral(data?.detail || err.message || 'Error al iniciar sesión')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: 48, height: 48,
            background: '#185FA5',
            borderRadius: 10,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 12,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M4 16L10 8L14 12L19 5"
                stroke="#fff" strokeWidth="2.2"
                strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <Title level={3} style={{ margin: 0 }}>QuantVisionGC</Title>
          <Text type="secondary" style={{ fontSize: 13 }}>
            Inicia sesión en tu cuenta
          </Text>
        </div>

        {errorGeneral && (
          <Alert type="error" message={errorGeneral} showIcon closable />
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          autoComplete="on"
          requiredMark={false}
        >
          <Form.Item
            label="Correo electrónico"
            name="correo"
            rules={[
              { required: true, message: 'Introduce tu correo' },
              { type: 'email', message: 'Formato de correo inválido' },
            ]}
          >
            <Input
              prefix={<MailOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="tu@correo.com"
              autoFocus
            />
          </Form.Item>

          <Form.Item
            label="Contraseña"
            name="password"
            rules={[{ required: true, message: 'Introduce tu contraseña' }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="••••••••"
            />
          </Form.Item>

          <Button
            type="primary"
            htmlType="submit"
            block
            loading={loading}
            size="large"
          >
            Iniciar sesión
          </Button>
        </Form>

        <div style={{ textAlign: 'center', fontSize: 13 }}>
          <Text type="secondary">¿No tienes cuenta? </Text>
          <Link to="/register">Regístrate</Link>
        </div>
      </Space>
    </AuthLayout>
  )
}
