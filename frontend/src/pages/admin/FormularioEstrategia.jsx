import { useEffect } from 'react'
import {
  Drawer, Form, Input, InputNumber, DatePicker, Select, AutoComplete, Button, Space, Row, Col,
} from 'antd'
import dayjs from 'dayjs'

const { TextArea } = Input

// Formulario Drawer para crear o editar una estrategia (RF-08, RF-09).
// El campo "estado" no se gestiona desde aquí: nuevas estrategias nacen "activa"
// y el cambio se hace después con el toggle de la tabla (RF-10).
export default function FormularioEstrategia({
  open, modo, estrategia, onClose, onGuardar,
  categoriasExistentes = [], tiposActivoExistentes = [], guardando = false,
}) {
  const [form] = Form.useForm()

  useEffect(() => {
    if (!open) return
    if (modo === 'edit' && estrategia) {
      form.setFieldsValue({
        nombre: estrategia.nombre,
        codigo_estrategia: estrategia.codigo_estrategia,
        descripcion: estrategia.descripcion,
        categoria: estrategia.categoria,
        tipo_activo: estrategia.tipo_activo,
        tipo: estrategia.tipo,
        nivel_riesgo: estrategia.nivel_riesgo,
        precio_subscripcion: Number(estrategia.precio_subscripcion),
        comision_ganancias: Number(estrategia.comision_ganancias),
        fecha_inicio: estrategia.fecha_inicio ? dayjs(estrategia.fecha_inicio) : null,
        fecha_fin:    estrategia.fecha_fin    ? dayjs(estrategia.fecha_fin)    : null,
      })
    } else {
      form.resetFields()
      form.setFieldsValue({
        tipo: 'estrategia_activa',
        nivel_riesgo: 4,
        precio_subscripcion: 9.99,
        comision_ganancias: 15,
      })
    }
  }, [open, modo, estrategia, form])

  const handleSubmit = async () => {
    let values
    try {
      values = await form.validateFields()
    } catch {
      return  // errores de validación, antd ya los muestra
    }

    if (values.fecha_fin && values.fecha_inicio && values.fecha_fin.isBefore(values.fecha_inicio, 'day')) {
      form.setFields([{ name: 'fecha_fin', errors: ['La fecha fin debe ser posterior a la fecha inicio'] }])
      return
    }

    const payload = {
      nombre:              values.nombre,
      descripcion:         values.descripcion || null,
      categoria:           values.categoria,
      tipo_activo:         values.tipo_activo,
      nivel_riesgo:        values.nivel_riesgo,
      precio_subscripcion: values.precio_subscripcion,
      comision_ganancias:  values.comision_ganancias,
      fecha_inicio:        values.fecha_inicio.format('YYYY-MM-DD'),
      codigo_estrategia:   values.codigo_estrategia,
      tipo:                values.tipo,
      fecha_fin:           values.fecha_fin ? values.fecha_fin.format('YYYY-MM-DD') : null,
    }
    if (modo === 'create') {
      payload.estado = 'activa'
    }
    await onGuardar(payload)
  }

  return (
    <Drawer
      title={modo === 'create' ? 'Crear estrategia' : `Editar: ${estrategia?.nombre || ''}`}
      open={open}
      onClose={onClose}
      width={560}
      destroyOnClose
      extra={
        <Space>
          <Button onClick={onClose}>Cancelar</Button>
          <Button type="primary" onClick={handleSubmit} loading={guardando}>
            {modo === 'create' ? 'Crear' : 'Guardar'}
          </Button>
        </Space>
      }
    >
      <Form form={form} layout="vertical" requiredMark>
        <Form.Item
          name="nombre"
          label="Nombre"
          rules={[
            { required: true, message: 'El nombre es obligatorio' },
            { min: 3, max: 100, message: 'Entre 3 y 100 caracteres' },
          ]}
        >
          <Input placeholder="Ej. AAPL ARIMA-GARCH" />
        </Form.Item>

        <Form.Item
          name="codigo_estrategia"
          label="Código (identificador único)"
          rules={[
            { required: true, message: 'El código es obligatorio' },
            { max: 50, message: 'Máximo 50 caracteres' },
          ]}
        >
          <Input placeholder="Ej. AAPL_arima_garch" />
        </Form.Item>

        <Form.Item name="descripcion" label="Descripción">
          <TextArea rows={3} placeholder="Descripción breve de la estrategia (opcional)" />
        </Form.Item>

        <Row gutter={12}>
          <Col span={12}>
            <Form.Item
              name="categoria"
              label="Categoría"
              rules={[
                { required: true, message: 'La categoría es obligatoria' },
                { max: 50, message: 'Máximo 50 caracteres' },
              ]}
            >
              <AutoComplete
                options={categoriasExistentes.map(c => ({ value: c }))}
                placeholder="classifier, arima_garch..."
                filterOption={(input, option) => option.value.toLowerCase().includes(input.toLowerCase())}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="tipo_activo"
              label="Tipo de activo"
              rules={[
                { required: true, message: 'El tipo de activo es obligatorio' },
                { max: 50, message: 'Máximo 50 caracteres' },
              ]}
            >
              <AutoComplete
                options={tiposActivoExistentes.map(t => ({ value: t }))}
                placeholder="accion, indice..."
                filterOption={(input, option) => option.value.toLowerCase().includes(input.toLowerCase())}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={12}>
          <Col span={12}>
            <Form.Item name="tipo" label="Tipo" rules={[{ required: true }]}>
              <Select
                options={[
                  { value: 'estrategia_activa', label: 'Estrategia activa' },
                  { value: 'benchmark',         label: 'Benchmark' },
                ]}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="nivel_riesgo"
              label="Nivel de riesgo (1-7, MiFID)"
              rules={[{ required: true, message: 'Obligatorio' }]}
            >
              <InputNumber min={1} max={7} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={12}>
          <Col span={12}>
            <Form.Item
              name="precio_subscripcion"
              label="Precio de suscripción"
              rules={[{ required: true, message: 'Obligatorio' }]}
            >
              <InputNumber min={0} step={0.01} precision={2} style={{ width: '100%' }} addonAfter="€" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="comision_ganancias"
              label="Comisión sobre ganancias"
              rules={[{ required: true, message: 'Obligatorio' }]}
            >
              <InputNumber min={0} max={100} step={0.01} precision={2} style={{ width: '100%' }} addonAfter="%" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={12}>
          <Col span={12}>
            <Form.Item
              name="fecha_inicio"
              label="Fecha inicio"
              rules={[{ required: true, message: 'Obligatoria' }]}
            >
              <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="fecha_fin" label="Fecha fin (opcional)">
              <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Drawer>
  )
}
