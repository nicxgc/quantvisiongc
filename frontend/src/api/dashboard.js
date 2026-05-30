import client from './client'

// GET /dashboard/kpis — KPIs agregados del usuario (RF-23).
export const getKPIs = () => client.get('/dashboard/kpis')

// GET /dashboard/actividad-reciente — feed de eventos recientes (RF-27).
export const getActividadReciente = () => client.get('/dashboard/actividad-reciente')
