import client from './client'

// GET /users/me/monedero/cantidades-permitidas — denominaciones para recarga (RF-46).
export const getCantidadesPermitidas = () => client.get('/users/me/monedero/cantidades-permitidas')

// POST /users/me/monedero/recargar — añade fondos al monedero virtual (RF-46).
export const recargar = (payload) => client.post('/users/me/monedero/recargar', payload)

// GET /users/me/monedero/movimientos — histórico paginado de movimientos (RF-47).
export const getMovimientos = () => client.get('/users/me/monedero/movimientos')
