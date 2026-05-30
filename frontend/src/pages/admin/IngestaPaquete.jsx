import { useState } from 'react'
import { Upload, Typography, App, Spin, Alert } from 'antd'
import { InboxOutlined, FileZipOutlined } from '@ant-design/icons'
import * as adminApi from '../../api/admin'

const { Dragger } = Upload
const { Paragraph, Text } = Typography

// Subida de paquetes ZIP con estrategias y resultados (RF-13 a RF-16).
// El backend valida estructura, contenido y persiste estrategias + series temporales.
export default function IngestaPaquete() {
  const { message } = App.useApp()
  const [uploading, setUploading] = useState(false)
  const [resultado, setResultado] = useState(null)
  const [error, setError]         = useState(null)
  const [archivo, setArchivo]     = useState(null)

  const handleUpload = async (file) => {
    setUploading(true)
    setResultado(null)
    setError(null)
    setArchivo({ name: file.name, size: file.size })
    try {
      const formData = new FormData()
      formData.append('archivo', file)
      const respuesta = await adminApi.subirPaquete(formData)
      setResultado(respuesta)
      message.success('Paquete procesado correctamente.')
    } catch (err) {
      const status = err.response?.status
      const data   = err.response?.data
      const detalleRaw =
        data?.detail ??
        data?.mensaje ??
        data?.error ??
        (typeof data === 'string' ? data : null) ??
        err.message ??
        'Error desconocido'
      const detalleStr = typeof detalleRaw === 'string' ? detalleRaw : JSON.stringify(detalleRaw, null, 2)

      let descripcion = detalleStr
      if (status === 409) {
        descripcion = `El paquete contiene estrategias o resultados que ya existen en el sistema (HTTP 409). Si quieres re-importar, primero hay que eliminar los registros conflictivos desde la gestión de estrategias.`
        if (detalleStr && detalleStr !== 'Request failed with status code 409') {
          descripcion += `\n\nDetalle del servidor: ${detalleStr}`
        }
      } else if (status === 413) {
        descripcion = 'El paquete es demasiado grande. Reduce su tamaño o divide la subida.'
      } else if (status === 415) {
        descripcion = 'Formato no soportado. El servidor solo acepta paquetes ZIP.'
      } else if (status === 422) {
        descripcion = `El paquete no pasó la validación del servidor (HTTP 422).\n\n${detalleStr}`
      } else if (err.code === 'ECONNABORTED' || /timeout/i.test(err.message)) {
        descripcion = 'El procesamiento del paquete excedió el tiempo máximo. Intenta de nuevo o reduce el tamaño del paquete.'
      }

      setError(descripcion)
      message.error('No se pudo procesar el paquete.')
    } finally {
      setUploading(false)
    }
    return false  // evita la subida nativa de antd
  }

  return (
    <div>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        Sube un paquete <Text code>.zip</Text> con las estrategias y sus resultados.
        El servidor validará el contenido y creará o actualizará los registros correspondientes.
      </Paragraph>

      <Dragger
        accept=".zip"
        beforeUpload={handleUpload}
        showUploadList={false}
        disabled={uploading}
        style={{ marginBottom: 16 }}
      >
        <p className="ant-upload-drag-icon"><InboxOutlined /></p>
        <p className="ant-upload-text">
          {uploading ? 'Procesando paquete…' : 'Haz clic o arrastra aquí el archivo ZIP'}
        </p>
        <p className="ant-upload-hint">Solo se aceptan archivos .zip generados por el pipeline de estrategias</p>
      </Dragger>

      {archivo && (
        <div style={{ marginBottom: 12, fontSize: 13 }}>
          <FileZipOutlined style={{ marginRight: 6, color: '#185FA5' }} />
          <Text strong>{archivo.name}</Text>
          <Text type="secondary" style={{ marginLeft: 8 }}>
            {(archivo.size / 1024).toFixed(1)} KB
          </Text>
        </div>
      )}

      {uploading && (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Spin size="large" tip="El servidor está procesando el paquete..." />
        </div>
      )}

      {error && (
        <Alert
          type="error"
          showIcon
          message="Error al procesar el paquete"
          description={error}
          style={{ marginTop: 12 }}
        />
      )}

      {resultado && !error && (
        <Alert
          type="success"
          showIcon
          message="Procesamiento completado"
          description={
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
                Respuesta del servidor:
              </Text>
              <pre style={{ fontSize: 11, background: '#fff', padding: 10, borderRadius: 4, maxHeight: 320, overflow: 'auto', margin: 0 }}>
                {typeof resultado === 'string' ? resultado : JSON.stringify(resultado, null, 2)}
              </pre>
            </div>
          }
          style={{ marginTop: 12 }}
        />
      )}
    </div>
  )
}
