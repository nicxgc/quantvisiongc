import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import * as authApi from '../api/auth'
import { TOKEN_KEY } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [token, setToken]     = useState(() => localStorage.getItem(TOKEN_KEY))
  const [isLoading, setIsLoading] = useState(true)

  // Al montar: si hay token guardado, verificar que sigue siendo válido
  // preguntando al backend con GET /users/me. Si el servidor lo rechaza,
  // se limpia para no dejar al usuario atrapado con un token expirado.
  useEffect(() => {
    const verificarSesion = async () => {
      const tokenGuardado = localStorage.getItem(TOKEN_KEY)
      if (!tokenGuardado) {
        setIsLoading(false)
        return
      }
      try {
        const userData = await authApi.getCurrentUser()
        setUser(userData)
      } catch {
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
      } finally {
        setIsLoading(false)
      }
    }
    verificarSesion()
  }, [])

  // Escuchar el evento emitido por el interceptor de Axios cuando llega
  // un 401 en cualquier petición. Borra la sesión sin que la vista
  // que hizo la petición tenga que encargarse de ello.
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null)
      setToken(null)
    }
    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized)
  }, [])

  // login: llama al backend, guarda el token, carga los datos del usuario.
  // Devuelve los datos del usuario para que la vista pueda redirigir
  // al destino correcto según el rol.
  const login = useCallback(async (email, password) => {
    const respuesta = await authApi.login(email, password)
    const { access_token } = respuesta
    localStorage.setItem(TOKEN_KEY, access_token)
    setToken(access_token)
    const userData = await authApi.getCurrentUser()
    setUser(userData)
    return userData
  }, [])

  // logout: intenta avisar al backend (para invalidar el token via
  // token versioning) y limpia el estado local independientemente
  // del resultado.
  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      // Si el backend falla, igualmente cerramos sesión en el cliente.
    } finally {
      localStorage.removeItem(TOKEN_KEY)
      setToken(null)
      setUser(null)
    }
  }, [])

  // Recarga los datos del usuario desde el backend. Útil tras operaciones
  // que cambian el saldo del monedero (contratación, cancelación, recarga)
  // para que el header refleje el saldo actualizado al instante.
  const refreshUser = useCallback(async () => {
    try {
      const userData = await authApi.getCurrentUser()
      setUser(userData)
      return userData
    } catch (err) {
      console.error('No se pudo refrescar el usuario', err)
    }
  }, [])

  const value = {
    user,
    token,
    isLoading,
    isAuthenticated: !!token && !!user,
    isAdmin: user?.rol === 'admin',
    login,
    logout,
    refreshUser,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

// Hook para consumir el contexto. Lanza un error explícito si se usa
// fuera del AuthProvider, lo que ayuda a detectar errores pronto.
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  }
  return context
}
