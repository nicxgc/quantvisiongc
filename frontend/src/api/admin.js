import client from './client'

// --- Gestión de usuarios (RF-06, RF-07) ---

// GET /users — listado de todos los usuarios registrados.
export const listarUsuarios = () => client.get('/users')

// DELETE /users/{id} — soft-delete de un usuario.
export const eliminarUsuario = (idUsuario) => client.delete(`/users/${idUsuario}`)

// --- Ingesta de paquete externo (RF-13 a RF-16) ---

// POST /admin/ingesta/paquete — sube un ZIP con resultados de estrategia.
export const subirPaquete = (formData) =>
  client.post('/admin/ingesta/paquete', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  })
