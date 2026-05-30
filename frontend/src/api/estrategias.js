import client from './client'

// --- Endpoints públicos y de usuario autenticado ---

// GET /estrategias — catálogo público con resumen out-of-sample.
export const getCatalogo = (params) => client.get('/estrategias', { params })

// GET /estrategias/{id} — detalle de una estrategia concreta.
export const getDetalle = (id) => client.get(`/estrategias/${id}`)

// GET /estrategias/{id}/resultados — serie temporal (equity, drawdown, retorno).
export const getResultados = (id) => client.get(`/estrategias/${id}/resultados`)

// --- Endpoints exclusivos de administrador ---

// GET /estrategias/admin — listado completo incluyendo inactivas.
export const getListadoAdmin = () => client.get('/estrategias/admin')

// POST /estrategias — crear estrategia (admin).
export const crear = (payload) => client.post('/estrategias', payload)

// PATCH /estrategias/{id} — editar estrategia (admin).
export const editar = (id, payload) => client.patch(`/estrategias/${id}`, payload)

// DELETE /estrategias/{id} — soft-delete con cascada (admin).
export const eliminar = (id) => client.delete(`/estrategias/${id}`)
