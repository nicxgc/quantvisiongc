import { useState, useEffect } from 'react'
import { Form, Input, Button, Typography, Alert, Space } from 'antd'
import { UserOutlined, MailOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import * as authApi from '../../api/auth'
import AuthLayout from '../../components/layout/AuthLayout'
import usePageTitle from '../../hooks/usePageTitle'

const { Title, Text } = Typography

// Página de registro (RF-01).
// Tras crear la cuenta hace auto-login para que el usuario entre directo
// al dashboard sin tener que volver a teclear las credenciales.
// El backend asigna automáticamente rol="user" (RF-02) y saldo=0 € (RF-39).
export default function Register() {
  usePageTitle('Crear cuenta')
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [errorGeneral, setErrorGeneral] = useState(null)

  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard', { replace: true })
  }, [isAuthenticated, navigate])

  const onFinish = async (values) => {
    setLoading(true)
    setErrorGeneral(null)
    try {
      // 1. Crear la cuenta en el backend
      await authApi.register({
        nombre_completo: values.nombre_completo,
        correo: values.correo,
        password: values.password,
      })

      // 2. Auto-login con las mismas credenciales
      await login(values.correo, values.password)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const status = err.response?.status
      const data   = err.response?.data

      if (status === 409) {
        // Correo ya registrado: error específico en el campo correo
        form.setFields([{
          name: 'correo',
          errors: [data?.detail || 'Este correo ya está registrado'],
        }])
      } else if (status === 422 && Array.isArray(data?.detail)) {
        // Errores Pydantic mapeados a sus campos
        const fields = data.detail
          .map(e => ({ name: e.loc?.[e.loc.length - 1], errors: [e.msg] }))
          .filter(f => f.name)
        form.setFields(fields)
      } else {
        setErrorGeneral(data?.detail || err.message || 'Error al crear la cuenta')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout width={440}>
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
            Crea tu cuenta para empezar
          </Text>
        </div>

        {errorGeneral && (
          <Alert type="error" message={errorGeneral} showIcon closable />
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          autoComplete="off"
          requiredMark={false}
        >
          <Form.Item
            label="Nombre completo"
            name="nombre_completo"
            rules={[
              { required: true, message: 'Introduce tu nombre' },
              { min: 2, message: 'El nombre debe tener al menos 2 caracteres' },
              { max: 100, message: 'Máximo 100 caracteres' },
            ]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="Nicolás Gil Castro"
              autoFocus
            />
          </Form.Item>

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
            />
          </Form.Item>

          <Form.Item
            label="Contraseña"
            name="password"
            rules={[
              { required: true, message: 'Introduce una contraseña' },
              { min: 8, message: 'Mínimo 8 caracteres' },
            ]}
            hasFeedback
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="Mínimo 8 caracteres"
            />
          </Form.Item>

          <Form.Item
            label="Confirmar contraseña"
            name="confirm_password"
            dependencies={['password']}
            hasFeedback
            rules={[
              { required: true, message: 'Confirma la contraseña' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('Las contraseñas no coinciden'))
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="Repite la contraseña"
            />
          </Form.Item>

          <Button
            type="primary"
            htmlType="submit"
            block
            loading={loading}
            size="large"
          >
            Crear cuenta
          </Button>
        </Form>

        <div style={{ textAlign: 'center', fontSize: 13 }}>
          <Text type="secondary">¿Ya tienes cuenta? </Text>
          <Link to="/login">Inicia sesión</Link>
        </div>
      </Space>
    </AuthLayout>
  )
}
