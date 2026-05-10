\# **Bitácora — Tarea 3: Desarrollo del backend y API REST segura**



\## **2026-05-09 (Sábado) — Subtarea 3.1 completada**



\### **Hecho**

\- Repo `quantvisiongc` creado en GitHub (privado) y clonado en `C:\\TFG\\quantvisiongc`.

\- Estructura inicial: `backend/`, `docs/evidencias/T3/`.

\- Entorno virtual de Python 3.11.9 creado en `backend/venv/`.

\- 12 dependencias instaladas con versiones pinadas en `requirements.txt`.

\- `docker-compose.yml` con servicio `db` basado en imagen `timescale/timescaledb:2.17.2-pg16`.

\- Variables de entorno externalizadas en `.env`, plantilla pública en `.env.example`, `.gitignore` configurado.

\- Contenedor levantado y verificado: estado `healthy`, extensión TimescaleDB activa.



\### **Decisiones tomadas**

\- Pinado exacto de dependencias (==) en lugar de rangos, para reproducibilidad.

\- Imagen TimescaleDB Community Edition (gratuita) sobre PostgreSQL 16.

\- Backend NO containerizado durante desarrollo (auto-reload y debugging más simples).

\- Credenciales sólo en `.env` (cubre driver DR-05 de la arquitectura).



\### **Tiempo invertido**

\~1h 30min (vs 5h previstas en planificación → ahorro de 3.5h)



\---------------------------------------------------------------------------------------------------------------------------------------------



\## **2026-05-10 (Domingo) — Subtarea 3.2 (parte 1: estructura backend)**



\### **Hecho**

\- Estructura completa del backend en `app/` siguiendo la arquitectura por 

&#x20; capas decidida en el capítulo 3 (core/, models/, schemas/, routers/, services/).

\- `app/core/config.py`: carga de configuración desde `.env` con 

&#x20; pydantic-settings, instancia singleton `settings`.

\- `app/core/database.py`: engine SQLAlchemy con pool de conexiones, 

&#x20; fábrica `SessionLocal`, `Base` declarativa, dependencia `get\_db()`.

\- `app/main.py`: aplicación FastAPI con metadatos, middleware CORS 

&#x20; restringido al frontend, registro de routers.

\- `app/routers/health.py`: endpoint GET /api/v1/health que verifica 

&#x20; conexión con BBDD ejecutando SELECT 1.

\- Servidor uvicorn levantado en http://localhost:8000.

\- Documentación interactiva auto-generada en /docs (Swagger UI).

\- Endpoint /health verificado con curl: respuesta 200 OK + JSON correcto.



\### **Decisiones técnicas e incidencias resueltas**



1\. \*\*Migración psycopg2 → psycopg3\*\*: el driver psycopg2 producía 

&#x20;  UnicodeDecodeError en el handshake de conexión bajo Windows con locale 

&#x20;  español. Se migró a psycopg3 (paquete `psycopg`), versión sucesora del 

&#x20;  mismo autor, con mejor soporte Unicode multiplataforma y mantenimiento 

&#x20;  activo. Cambio: dependencia + dialecto SQLAlchemy de `postgresql+psycopg2://` 

&#x20;  a `postgresql+psycopg://`.



2\. \*\*Conflicto en el puerto 5432\*\*: durante la verificación se detectó que 

&#x20;  una instalación nativa de PostgreSQL en el sistema operativo escuchaba 

&#x20;  en el mismo puerto 5432 que el contenedor Docker, interceptando las 

&#x20;  conexiones del backend Python antes de que llegaran al contenedor. 

&#x20;  Solución: mapear el contenedor al puerto 5433 del host (`"5433:5432"` 

&#x20;  en docker-compose.yml) para evitar el conflicto sin afectar a la 

&#x20;  instalación nativa, que puede ser utilizada por otros proyectos. Esta 

&#x20;  práctica es estándar en entornos donde múltiples proyectos comparten 

&#x20;  una misma máquina de desarrollo.



3\. \*\*Configuración pydantic-settings con `extra="ignore"`\*\*: el archivo 

&#x20;  `.env` contiene variables que solo usa Docker Compose (POSTGRES\_USER, 

&#x20;  POSTGRES\_PASSWORD, POSTGRES\_DB) y no la aplicación Python. Por defecto 

&#x20;  pydantic v2 trata las variables no declaradas como errores; añadido 

&#x20;  `extra="ignore"` en `SettingsConfigDict` para tolerarlas silenciosamente.



4\. \*\*Elección de SQLAlchemy en modo síncrono\*\*: aunque FastAPI permite 

&#x20;  código asíncrono, se ha optado por sesiones síncronas por simplicidad 

&#x20;  y porque el rendimiento esperado del sistema (TFG con un único 

&#x20;  desarrollador y bajo tráfico) no justifica la complejidad adicional de 

&#x20;  un código asíncrono completo (sesiones async, await en todas las 

&#x20;  operaciones de BBDD, etc.).



\### **Aprendizajes metodológicos**

\- Diagnóstico sistemático con `netstat -ano | findstr :5432` reveló dos 

&#x20; procesos en el mismo puerto, lo que apuntó al conflicto.

\- Los logs de PostgreSQL del contenedor confirmaron que las peticiones 

&#x20; Python no llegaban al servidor, descartando un problema de credenciales 

&#x20; y orientando la investigación hacia la red.

\- Uso de `repr()` para inspeccionar strings con caracteres potencialmente 

&#x20; invisibles (espacios, retornos de carro) durante el debugging.



\### **Pendiente para esta tarde**

\- Configurar Alembic para migraciones de base de datos.

\- Verificar primera migración vacía aplicada correctamente.

\- Commit final de la subtarea 3.2.



\### **Tiempo invertido**

\~6 h (vs 5 h previstas en el plan) — desviación causada por las 

incidencias de entorno (todas resueltas y documentadas).

