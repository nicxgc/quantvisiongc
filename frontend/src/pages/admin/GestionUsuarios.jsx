import { useState, useEffect, useMemo } from 'react'
import {
  Table, Tag, Button, Typography, Spin, Alert, Empty, App, Input, Select, Space, Row, Col,
} from 'antd'
import { DeleteOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { useAuth } from '../../context/AuthContext'
import * as adminApi from '../../api/admin'
import { formatEuros, formatFecha } from '../../utils/formatters'

const { Text, Paragraph } = Typography

// Gestión de usuarios para administradores (RF-06 listar, RF-07 soft-delete).
// El backend cancela en cascada las contrataciones activas y devuelve el saldo.
export default function GestionUsuarios() {
  const { user } = useAuth()
  const { message, modal } = App.useApp()

  const [usuarios, setUsuarios]           = useState([])
  const [loading, setLoading]             = useState(true)
  const [error, setError]                 = useState(null)
  const [busqueda, setBusqueda]           = useState('')
  const [filtroEstado, setFiltroEstado]   = useState('activos') // activos | eliminados | todos
  const [filtroRol, setFiltroRol]         = useState('todos')   // todos | user | admin

  const cargar = async () => {
    setLoading(true)
    setError(null)
    try {
      const lista = await adminApi.listarUsuarios()
      setUsuarios(Array.isArray(lista) ? lista : [])
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'No se pudieron cargar los usuarios')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { cargar() }, [])

  const handleEliminar = (u) => {
    modal.confirm({
      title: 'Eliminar usuario',
      width: 460,
      content: (
        <div style={{ marginTop: 12 }}>
          <p>¿Seguro que quieres eliminar a <strong>{u.nombre_completo}</strong> ({u.correo})?</p>
          <p style={{ color: '#888', fontSize: 13 }}>
            El usuario quedará marcado como inactivo. Sus contrataciones activas se cancelarán automáticamente
            y se le devolverá el importe correspondiente a su monedero. La operación se puede revertir desde la base de datos.
          </p>
        </div>
      ),
      okText: 'Sí, eliminar',
      okButtonProps: { danger: true },
      cancelText: 'No',
      onOk: async () => {
        try {
          await adminApi.eliminarUsuario(u.id)
          message.success(`Usuario "${u.nombre_completo}" eliminado.`)
          await cargar()
        } catch (err) {
          const detalle = err.response?.data?.detail
          message.error(typeof detalle === 'string' ? detalle : 'No se pudo eliminar el usuario.')
        }
      },
    })
  }

  const filtrados = useMemo(() => {
    const q = busqueda.trim().toLowerCase()
    return usuarios
      .filter(u => {
        if (filtroEstado === 'activos'    && !u.activa) return false
        if (filtroEstado === 'eliminados' &&  u.activa) return false
        if (filtroRol !== 'todos' && u.rol !== filtroRol) return false
        if (q) {
          const nombre = (u.nombre_completo || '').toLowerCase()
          const correo = (u.correo || '').toLowerCase()
          if (!nombre.includes(q) && !correo.includes(q)) return false
        }
        return true
      })
      .sort((a, b) => new Date(b.fecha_registro) - new Date(a.fecha_registro))
  }, [usuarios, busqueda, filtroEstado, filtroRol])

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    {
      title: 'Nombre',
      dataIndex: 'nombre_completo',
      key: 'nombre',
      render: (n, u) => (
        <Space size={6}>
          <Text strong>{n}</Text>
          {u.id === user?.id && <Tag color="blue" style={{ fontSize: 10 }}>Tú</Tag>}
        </Space>
      ),
    },
    { title: 'Correo', dataIndex: 'correo', key: 'correo' },
    {
      title: 'Rol',
      dataIndex: 'rol',
      key: 'rol',
      width: 100,
      render: (r) => <Tag color={r === 'admin' ? 'gold' : 'default'}>{r === 'admin' ? 'Admin' : 'Usuario'}</Tag>,
    },
    {
      title: 'Saldo',
      dataIndex: 'saldo_monedero',
      key: 'saldo_monedero',
      align: 'right',
      render: (s) => formatEuros(s),
    },
    {
      title: 'Registro',
      dataIndex: 'fecha_registro',
      key: 'fecha_registro',
      render: (f) => formatFecha(f, 'DD MMM YYYY'),
    },
    {
      title: 'Estado',
      dataIndex: 'activa',
      key: 'activa',
      width: 110,
      render: (a) => <Tag color={a ? 'success' : 'default'}>{a ? 'Activo' : 'Eliminado'}</Tag>,
    },
    {
      title: 'Acción',
      key: 'accion',
      width: 130,
      render: (_, u) => {
        if (!u.activa) return <Text type="secondary" style={{ fontSize: 12 }}>—</Text>
        if (u.id === user?.id) return <Text type="secondary" style={{ fontSize: 12 }}>(uno mismo)</Text>
        return (
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleEliminar(u)}>
            Eliminar
          </Button>
        )
      },
    },
  ]

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
  }

  return (
    <div>
      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}

      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={10}>
          <Input
            placeholder="Buscar por nombre o correo"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            allowClear
            prefix={<SearchOutlined style={{ color: '#999' }} />}
          />
        </Col>
        <Col xs={12} md={6}>
          <Select
            value={filtroEstado}
            onChange={setFiltroEstado}
            style={{ width: '100%' }}
            options={[
              { value: 'activos',    label: 'Solo activos' },
              { value: 'eliminados', label: 'Solo eliminados' },
              { value: 'todos',      label: 'Todos' },
            ]}
          />
        </Col>
        <Col xs={12} md={5}>
          <Select
            value={filtroRol}
            onChange={setFiltroRol}
            style={{ width: '100%' }}
            options={[
              { value: 'todos', label: 'Todos los roles' },
              { value: 'user',  label: 'Usuarios' },
              { value: 'admin', label: 'Administradores' },
            ]}
          />
        </Col>
        <Col xs={24} md={3}>
          <Button icon={<ReloadOutlined />} onClick={cargar} block>Recargar</Button>
        </Col>
      </Row>

      <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
        Mostrando {filtrados.length} de {usuarios.length} usuarios.
      </Paragraph>

      {filtrados.length === 0 ? (
        <Empty description="No hay usuarios que coincidan con los filtros" />
      ) : (
        <Table
          rowKey="id"
          columns={columns}
          dataSource={filtrados}
          pagination={{ pageSize: 15, hideOnSinglePage: true }}
          size="middle"
          scroll={{ x: 'max-content' }}
        />
      )}
    </div>
  )
}
