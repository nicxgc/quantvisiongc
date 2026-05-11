# Bitácora — Tarea 3: Desarrollo del backend y API REST segura

---

## 2026-05-09 (Sábado) — Subtarea 3.1: configuración del entorno

### Qué he hecho

- Creado el repositorio `quantvisiongc` en GitHub (privado) y clonado en `C:\TFG\quantvisiongc`.
- Estructura inicial del proyecto: `backend/` y `docs/evidencias/T3/`.
- Entorno virtual de Python 3.11.9 creado en `backend/venv/`.
- 12 dependencias instaladas con versiones pinadas en `requirements.txt`.
- `docker-compose.yml` con servicio `db` basado en la imagen `timescale/timescaledb:2.17.2-pg16`.
- Variables de entorno externalizadas en `.env`, plantilla pública en `.env.example` y `.gitignore` configurado.
- Contenedor levantado y verificado: estado `healthy`, extensión TimescaleDB activa.

### Decisiones tomadas

- **Pinado exacto de dependencias (`==`)** en lugar de rangos, para garantizar reproducibilidad.
- **Imagen TimescaleDB Community Edition** (gratuita) sobre PostgreSQL 16.
- **Backend no contenedorizado durante desarrollo.** El auto-reload de uvicorn y el debugging son más cómodos ejecutando el backend directamente desde el venv local.
- **Credenciales solo en `.env`.** Cubre el driver DR-05 de la arquitectura (configuración externa al código).

### Tiempo invertido

~1 h 30 min (frente a las 5 h previstas en la planificación → ahorro de 3 h 30 min).

---

## 2026-05-10 (Domingo) — Subtarea 3.2: esqueleto del backend y migraciones

Por su volumen, divido la jornada en dos bloques: primero el levantamiento del esqueleto FastAPI y la verificación del servidor, y después la configuración de Alembic.

### Bloque 1 — Esqueleto FastAPI y conexión con la BBDD

#### Qué he hecho

- Estructura completa del backend en `app/`, siguiendo la arquitectura por capas decidida en el capítulo 3: `core/`, `models/`, `schemas/`, `routers/`, `services/`.
- `app/core/config.py`: carga de configuración desde `.env` con pydantic-settings e instancia singleton `settings`.
- `app/core/database.py`: engine SQLAlchemy con pool de conexiones, fábrica `SessionLocal`, `Base` declarativa y dependencia `get_db()`.
- `app/main.py`: aplicación FastAPI con metadatos, middleware CORS restringido al frontend y registro de routers.
- `app/routers/health.py`: endpoint `GET /api/v1/health` que verifica la conexión con la BBDD ejecutando un `SELECT 1`.
- Servidor uvicorn levantado en `http://localhost:8000`.
- Documentación interactiva auto-generada en `/docs` (Swagger UI).
- Endpoint `/health` verificado con `curl`: respuesta `200 OK` y JSON correcto.

#### Decisiones técnicas e incidencias resueltas

1. **Migración de psycopg2 a psycopg3.** El driver psycopg2 producía `UnicodeDecodeError` en el handshake de conexión bajo Windows con locale español. Migré a psycopg3 (paquete `psycopg`), versión sucesora del mismo autor, con mejor soporte Unicode multiplataforma y mantenimiento activo. El cambio implicó actualizar la dependencia y modificar el dialecto SQLAlchemy de `postgresql+psycopg2://` a `postgresql+psycopg://`.

2. **Conflicto en el puerto 5432.** Durante la verificación detecté que una instalación nativa de PostgreSQL escuchaba en el mismo puerto 5432 que el contenedor Docker, interceptando las conexiones del backend antes de que llegaran al contenedor. Solución: mapear el contenedor al puerto 5433 del host (`"5433:5432"` en `docker-compose.yml`) para evitar el conflicto sin afectar a la instalación nativa. Es una práctica estándar cuando varios proyectos comparten una misma máquina de desarrollo.

3. **Configuración de pydantic-settings con `extra="ignore"`.** El archivo `.env` contiene variables que solo usa Docker Compose (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) y no la aplicación Python. Por defecto pydantic v2 trata las variables no declaradas como errores; añadí `extra="ignore"` en `SettingsConfigDict` para tolerarlas silenciosamente.

4. **SQLAlchemy en modo síncrono.** Aunque FastAPI permite código asíncrono, opto por sesiones síncronas por simplicidad. El rendimiento esperado del sistema (TFG con un único desarrollador y bajo tráfico) no justifica la complejidad adicional de un código asíncrono completo (sesiones async, `await` en todas las operaciones de BBDD, etc.).

#### Aprendizajes metodológicos

- El diagnóstico sistemático con `netstat -ano | findstr :5432` reveló dos procesos en el mismo puerto, lo que apuntó directamente al conflicto.
- Los logs de PostgreSQL del contenedor confirmaron que las peticiones del backend Python no llegaban al servidor, descartando un problema de credenciales y orientando la investigación hacia la red.
- Uso de `repr()` para inspeccionar strings con caracteres potencialmente invisibles (espacios, retornos de carro) durante el debugging.

### Bloque 2 — Configuración de Alembic

#### Qué he hecho

- Inicializado Alembic dentro de `backend/` con `alembic init alembic`. Se han creado la carpeta `alembic/` (con `env.py`, `script.py.mako` y `versions/`) y el archivo `alembic.ini`.
- Editado `alembic.ini` para quitar la línea `sqlalchemy.url`, porque la URL la cargo desde el código a través de `settings`.
- Editado `alembic/env.py` para:
  - Añadir `sys.path.insert(...)` al principio para que se pueda importar `app.core.config` desde dentro de la carpeta `alembic/`.
  - Importar `settings` (de `app.core.config`) y `Base` (de `app.core.database`).
  - Configurar `target_metadata = Base.metadata` para que Alembic detecte los modelos cuando los registre.
  - Llamar a `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)` antes del `context.configure(...)`, tanto en `run_migrations_online` como en `run_migrations_offline`.
  - Dejar preparado (comentado) el bloque de imports de modelos: `# from app.models import usuario, estrategia, resultado_estrategia, contratacion`. Lo descomentaré mañana al crear las cuatro entidades.
- Generada primera migración vacía con `alembic revision -m "inicial - configuracion alembic"` (hash `1494b60d30a9`).
- Aplicada con `alembic upgrade head`. Esto ha creado la tabla `alembic_version` en la BBDD, que es donde Alembic lleva el control de qué migraciones se han ejecutado.

#### Decisiones tomadas

- **URL de la BBDD cargada desde código y no desde `alembic.ini`.** Así no duplico la configuración (ya vive en `app/core/config.py`, leída del `.env`) y mantengo un único punto de verdad. Si en el futuro cambio el puerto o las credenciales, solo tengo que tocar el `.env`.
- **Primera migración vacía intencionalmente.** Quería verificar que el sistema de migraciones funciona antes de meter modelos. Si hubiera generado los modelos primero y algo fallara en Alembic, sería más difícil aislar dónde está el problema.
- **Imports de modelos comentados.** Si los dejara descomentados ahora apuntando a módulos que aún no existen, fallaría cualquier comando de Alembic. Los descomento mañana al crear los modelos.

#### Verificación

- `alembic current` devuelve `1494b60d30a9 (head)`.
- `\dt` en la BBDD muestra la tabla `alembic_version`.
- `SELECT * FROM alembic_version` muestra una fila con el hash `1494b60d30a9`, que coincide con el de la migración.
- El servidor uvicorn sigue arrancando y `/api/v1/health` responde `200 OK`, confirmando que los cambios en `env.py` no han roto los imports de `app.core`.

### Evidencias del día

| Archivo | Contenido |
|---|---|
| `docs/evidencias/T3/05_endpoint_root.png` | Respuesta JSON del endpoint raíz `/`. |
| `docs/evidencias/T3/06_swagger_docs.png` | Documentación Swagger UI en `/docs`. |
| `docs/evidencias/T3/07_endpoint_health_ok.png` | Endpoint `/api/v1/health` respondiendo `200 OK`. |
| `docs/evidencias/T3/08_uvicorn_logs.png` | Logs del servidor con las peticiones registradas. |
| `docs/evidencias/T3/09_alembic_env_py.png` | Contenido final de `alembic/env.py`. |
| `docs/evidencias/T3/10_alembic_current.png` | Salida de `alembic current` mostrando `(head)`. |
| `docs/evidencias/T3/11_alembic_version_table.png` | Tabla `alembic_version` en psql con su contenido. |
| `docs/evidencias/T3/12_alembic_estructura.png` | Estructura de carpetas generada por Alembic. |

### Tiempo invertido

~7 h 30 min en total (≈6 h de esqueleto + verificación + incidencias y ≈1 h 30 min de Alembic + capturas + bitácora). La desviación frente a las 5 h previstas se justifica por las incidencias de entorno (psycopg2, puerto 5432), todas resueltas y documentadas.

### Estado al cierre del día

Subtarea 3.2 cerrada. Mañana lunes 11/05 empiezo con las subtareas 3.5 y 3.6: modelos SQLAlchemy de las cuatro entidades (`usuario`, `estrategia`, `resultado_estrategia`, `contratacion`), primera migración real con `--autogenerate` y schemas Pydantic base.

---