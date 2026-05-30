import client from './client'

// POST /auth/login — OAuth2 password flow, requiere form-urlencoded.
// El backend espera los campos 'username' (correo) y 'password'.
export const login = (email, password) => {
  const formData = new URLSearchParams()
  formData.append('username', email)
  formData.append('password', password)
  return client.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

// POST /auth/logout — invalida el JWT mediante token versioning en el backend.
export const logout = () => client.post('/auth/logout')

// POST /users/register — crea una cuenta nueva con saldo inicial 0 €.
export const register = (payload) => client.post('/users/register', payload)

// GET /users/me — datos del usuario autenticado (incluye saldo del monedero).
export const getCurrentUser = () => client.get('/users/me')
