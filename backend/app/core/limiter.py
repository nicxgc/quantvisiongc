from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiter compartido en toda la aplicación.
# key_func = get_remote_address: el límite se aplica por IP del cliente.
# Si en un despliegue real hay reverse proxy (nginx), get_remote_address
# usa el header X-Forwarded-For automáticamente.
limiter = Limiter(key_func=get_remote_address)
