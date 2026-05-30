import client from './client'

// POST /contrataciones — contratar una estrategia.
export const crear = (payload) => client.post('/contrataciones', payload)

// GET /contrataciones/mis-contrataciones — listado del usuario autenticado.
export const misContrataciones = () => client.get('/contrataciones/mis-contrataciones')

// PATCH /contrataciones/{id}/cancelar — cancelar una contratación propia.
export const cancelar = (idContratacion) =>
  client.patch(`/contrataciones/${idContratacion}/cancelar`)
