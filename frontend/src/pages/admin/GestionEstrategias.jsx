import { useState, useEffect, useMemo } from 'react'
import {
  Table, Tag, Button, Typography, Spin, Alert, Empty, App, Input, Select, Space, Row, Col, Switch,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, ReloadOutlined,
} from '@ant-design/icons'
import * as estrategiasApi from '../../api/estrategias'
import { formatEuros } from '../../utils/formatters'
import FormularioEstrategia from './FormularioEstrategia'

const { Text, Paragraph } = Typography

// Gestión administrativa de estrategias (RF-08 crear, RF-09 editar,
// RF-10 toggle activa/inactiva, RF-11 listar todas, RF-12 soft-delete).
export default function GestionEstrategias() {
  const { message, modal } = App.useApp()

  const [estrategias, setEstrategias]   = useState([])
  const [loading, setLoading]           = useState(true)
  const [error, setError]               = useState(null)
  const [busqueda, setBusqueda]         = useState('')
  const [filtroEstado, setFiltroEstado]     = useState('todas')    // activas | pausadas | todas
  const [filtroTipo, setFiltroTipo]         = useState('todos')    // todos | estrategia_activa | benchmark
  const [filtroVigencia, setFiltroVigencia] = useState('vigentes') // vigentes | eliminadas | todas

  const [drawerAbierto, setDrawerAbierto]       = useState(false)
  const [modoForm, setModoForm]                 = useState('create')
  const [estrategiaEditada, setEstrategiaEditada] = useState(null)
  const [guardando, setGuardando]               = useState(false)

  const cargar = async () => {
    setLoading(true)
    setError(null)
    try {
      const lista = await estrategiasApi.getListadoAdmin()
      setEstrategias(Array.isArray(lista) ? lista : [])
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'No se pudieron cargar las estrategias')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { cargar() }, [])

  const categoriasExistentes  = useMemo(
    () => [...new Set(estrategias.map(e => e.categoria).filter(Boolean))].sort(),
    [estrategias]
  )
  const tiposActivoExistentes = useMemo(
    () => [...new Set(estrategias.map(e => e.tipo_activo).filter(Boolean))].sort(),
    [estrategias]
  )

  const handleCrear = () => {
    setModoForm('create')
    setEstrategiaEditada(null)
    setDrawerAbierto(true)
  }

  const handleEditar = (est) => {
    setModoForm('edit')
    setEstrategiaEditada(est)
    setDrawerAbierto(true)
  }

  const handleToggleEstado = async (est) => {
    const nuevoEstado = est.estado === 'activa' ? 'pausada' : 'activa'
    // El backend no admite PATCH parcial: mandamos el payload completo.
    const payload = {
      nombre:              est.nombre,
      descripcion:         est.descripcion,
      categoria:           est.categoria,
      tipo_activo:         est.tipo_activo,
      nivel_riesgo:        est.nivel_riesgo,
      precio_subscripcion: Number(est.precio_subscripcion),
      comision_ganancias:  Number(est.comision_ganancias),
      fecha_inicio:        est.fecha_inicio,
      codigo_estrategia:   est.codigo_estrategia,
      tipo:                est.tipo,
      fecha_fin:           est.fecha_fin,
      estado:              nuevoEstado,
    }
    try {
      await estrategiasApi.editar(est.id, payload)
      message.success(`Estrategia ${nuevoEstado === 'activa' ? 'activada' : 'pausada'}.`)
      await cargar()
    } catch (err) {
      const det = err.response?.data?.detail
      let msg
      if (typeof det === 'string') {
        msg = det
      } else if (Array.isArray(det)) {
        // FastAPI 422: array de errores de validación
        msg = det.map(d => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ')
      } else if (det) {
        msg = JSON.stringify(det)
      } else {
        msg = err.message || 'No se pudo cambiar el estado.'
      }
      message.error(msg)
    }
  }

  const handleEliminar = (est) => {
    const aviso = est.num_contrataciones_activas > 0
      ? `Esta estrategia tiene ${est.num_contrataciones_activas} contratación(es) activa(s). Al eliminarla se cancelarán y se devolverá el importe a los usuarios afectados.`
      : 'Se marcará como eliminada (soft-delete). La operación se puede revertir desde la base de datos.'

    modal.confirm({
      title: 'Eliminar estrategia',
      width: 480,
      content: (
        <div style={{ marginTop: 12 }}>
          <p>¿Seguro que quieres eliminar <strong>{est.nombre}</strong>?</p>
          <p style={{ color: '#888', fontSize: 13 }}>{aviso}</p>
        </div>
      ),
      okText: 'Sí, eliminar',
      okButtonProps: { danger: true },
      cancelText: 'No',
      onOk: async () => {
        try {
          await estrategiasApi.eliminar(est.id)
          message.success(`Estrategia "${est.nombre}" eliminada.`)
          await cargar()
        } catch (err) {
          const det = err.response?.data?.detail
          message.error(typeof det === 'string' ? det : 'No se pudo eliminar la estrategia.')
        }
      },
    })
  }

  const handleGuardar = async (payload) => {
    setGuardando(true)
    try {
      if (modoForm === 'create') {
        await estrategiasApi.crear(payload)
        message.success('Estrategia creada correctamente.')
      } else {
        await estrategiasApi.editar(estrategiaEditada.id, payload)
        message.success('Estrategia actualizada.')
      }
      setDrawerAbierto(false)
      await cargar()
    } catch (err) {
      const det = err.response?.data?.detail
      const msg = typeof det === 'string' ? det : (typeof det === 'object' ? JSON.stringify(det) : err.message)
      message.error(msg || 'No se pudo guardar la estrategia.')
    } finally {
      setGuardando(false)
    }
  }

  const filtradas = useMemo(() => {
    const q = busqueda.trim().toLowerCase()
    return estrategias.filter(e => {
      if (filtroVigencia === 'vigentes'   && !e.activa) return false
      if (filtroVigencia === 'eliminadas' &&  e.activa) return false
      if (filtroEstado === 'activas'   && e.estado !== 'activa')   return false
      if (filtroEstado === 'pausadas' && e.estado !== 'pausada') return false
      if (filtroTipo !== 'todos' && e.tipo !== filtroTipo) return false
      if (q) {
        const n = (e.nombre || '').toLowerCase()
        const c = (e.codigo_estrategia || '').toLowerCase()
        if (!n.includes(q) && !c.includes(q)) return false
      }
      return true
    })
  }, [estrategias, busqueda, filtroEstado, filtroTipo, filtroVigencia])

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    {
      title: 'Nombre',
      key: 'nombre',
      render: (_, e) => (
        <Space size={6}>
          <Text strong>{e.nombre}</Text>
          {e.tipo === 'benchmark' && <Tag color="default" style={{ fontSize: 10 }}>Benchmark</Tag>}
        </Space>
      ),
    },
    { title: 'Código', dataIndex: 'codigo_estrategia', key: 'codigo_estrategia' },
    { title: 'Categoría', dataIndex: 'categoria', key: 'categoria' },
    {
      title: 'Riesgo',
      dataIndex: 'nivel_riesgo',
      key: 'nivel_riesgo',
      width: 80,
      align: 'center',
      render: (n) => <Tag color={n <= 2 ? 'green' : n <= 4 ? 'gold' : 'red'}>{n}</Tag>,
    },
    {
      title: 'Precio',
      dataIndex: 'precio_subscripcion',
      key: 'precio_subscripcion',
      width: 100,
      align: 'right',
      render: (p) => formatEuros(p),
    },
    {
      title: 'Estado',
      key: 'estado',
      width: 140,
      render: (_, e) => (
        <Space size={6}>
          <Switch
            size="small"
            checked={e.estado === 'activa'}
            onChange={() => handleToggleEstado(e)}
            disabled={!e.activa}
          />
          <Tag color={e.estado === 'activa' ? 'success' : 'default'}>
            {e.estado === 'activa' ? 'Activa' : 'Pausada'}
          </Tag>
        </Space>
      ),
    },
    {
      title: 'Vigencia',
      key: 'vigencia',
      width: 110,
      render: (_, e) => <Tag color={e.activa ? 'success' : 'default'}>{e.activa ? 'Vigente' : 'Eliminada'}</Tag>,
    },
    {
      title: 'Contratos',
      dataIndex: 'num_contrataciones_activas',
      key: 'num_contrataciones_activas',
      width: 90,
      align: 'center',
      render: (n) => (n > 0 ? <Tag color="blue">{n}</Tag> : <Text type="secondary">0</Text>),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      width: 180,
      render: (_, e) => (
        <Space size={4}>
          <Button size="small" icon={<EditOutlined />}   onClick={() => handleEditar(e)}   disabled={!e.activa}>Editar</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleEliminar(e)} disabled={!e.activa}>Eliminar</Button>
        </Space>
      ),
    },
  ]

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
  }

  return (
    <div>
      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}

      <Row gutter={[12, 12]} style={{ marginBottom: 16 }} align="middle">
        <Col xs={24} md={7}>
          <Input
            placeholder="Buscar por nombre o código"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            allowClear
            prefix={<SearchOutlined style={{ color: '#999' }} />}
          />
        </Col>
        <Col xs={8} md={4}>
          <Select value={filtroEstado} onChange={setFiltroEstado} style={{ width: '100%' }}
            options={[
              { value: 'todas',     label: 'Estado: todos' },
              { value: 'activas',   label: 'Solo activas' },
              { value: 'pausadas', label: 'Solo pausadas' },
            ]}
          />
        </Col>
        <Col xs={8} md={4}>
          <Select value={filtroTipo} onChange={setFiltroTipo} style={{ width: '100%' }}
            options={[
              { value: 'todos',             label: 'Tipo: todos' },
              { value: 'estrategia_activa', label: 'Estrategias' },
              { value: 'benchmark',         label: 'Benchmarks' },
            ]}
          />
        </Col>
        <Col xs={8} md={4}>
          <Select value={filtroVigencia} onChange={setFiltroVigencia} style={{ width: '100%' }}
            options={[
              { value: 'vigentes',   label: 'Vigentes' },
              { value: 'eliminadas', label: 'Eliminadas' },
              { value: 'todas',      label: 'Todas' },
            ]}
          />
        </Col>
        <Col xs={12} md={2}>
          <Button icon={<ReloadOutlined />} onClick={cargar} block>Recargar</Button>
        </Col>
        <Col xs={12} md={3}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCrear} block>Crear estrategia</Button>
        </Col>
      </Row>

      <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
        Mostrando {filtradas.length} de {estrategias.length} estrategias.
      </Paragraph>

      {filtradas.length === 0 ? (
        <Empty description="No hay estrategias que coincidan con los filtros" />
      ) : (
        <Table
          rowKey="id"
          columns={columns}
          dataSource={filtradas}
          pagination={{ pageSize: 15, hideOnSinglePage: true }}
          size="middle"
          scroll={{ x: 'max-content' }}
        />
      )}

      <FormularioEstrategia
        open={drawerAbierto}
        modo={modoForm}
        estrategia={estrategiaEditada}
        onClose={() => setDrawerAbierto(false)}
        onGuardar={handleGuardar}
        categoriasExistentes={categoriasExistentes}
        tiposActivoExistentes={tiposActivoExistentes}
        guardando={guardando}
      />
    </div>
  )
}
