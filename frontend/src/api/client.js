import axios from 'axios'

// Clave bajo la cual se guarda el JWT en localStorage. Se exporta porque
// AuthContext (T5.3) la usará para escribir el token tras hacer login.
export const TOKEN_KEY = 'quantvisiongc_token'

// Instancia única de Axios reutilizada por todos los módulos de api/.
// La baseURL se lee de la variable de entorno VITE_API_URL (.env),
// lo que permite cambiar el destino sin tocar código.
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// --- Interceptor de petición ---
// Antes de enviar cualquier petición, si hay token en localStorage lo
// añade al header Authorization en formato Bearer.
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// --- Interceptor de respuesta ---
// En caso de éxito devuelve directamente response.data para que las
// vistas reciban el cuerpo sin tener que hacer .data en cada llamada.
// En caso de error 401, limpia el token y emite un evento global
// 'auth:unauthorized' que AuthContext (T5.3) escuchará para redirigir
// al login. El resto de errores se propagan para que los maneje quien llamó.
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (!error.response) {
      // Error de red, timeout, CORS, backend caído.
      console.error('[API] Error de red:', error.message)
      return Promise.reject(error)
    }

    const { status } = error.response

    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    }

    return Promise.reject(error)
  }
)

export default client
