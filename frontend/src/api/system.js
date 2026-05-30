import client from './client'

// GET /health — smoke test de conectividad con el backend.
export const getHealth = () => client.get('/health')
