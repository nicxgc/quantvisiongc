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


---

## 2026-05-11 (Lunes) — Subtareas 3.5 y 3.6: modelos, migración inicial y schemas

Jornada con tres bloques encadenados: primero los modelos SQLAlchemy de las 4 entidades, después la primera migración real con `--autogenerate`, y al final los schemas Pydantic. Resuelta una incidencia interesante de comportamiento por defecto de SQLAlchemy con enums.

### Bloque 1 — Modelos SQLAlchemy

#### Qué he hecho

- Creado `backend/app/models/` con los 4 modelos correspondientes a las Tablas 3.27, 3.28+3.29+3.30, 3.31 y 3.32 de la memoria:
  - `usuario.py` — entidad fuerte con su `RolUsuario(str, Enum)`.
  - `estrategia.py` — entidad fuerte con 25 atributos organizados en 3 bloques separados por comentarios (descriptivos, métricas resumen y escenarios históricos), y enum `EstadoEstrategia`.
  - `resultado_estrategia.py` — entidad débil con PK compuesta `(id_estrategia, fecha)` declarada vía `PrimaryKeyConstraint` en `__table_args__`.
  - `contratacion.py` — entidad asociativa con id propio y enum `EstadoContratacion`.
- Sintaxis moderna de SQLAlchemy 2.0 en todos los modelos: `Mapped[...]` + `mapped_column()` con type hints completos.
- `app/models/__init__.py` que reexporta las 4 clases y sus enums, para que Alembic los detecte vía el import en `env.py`.
- Descomentado el import de modelos en `alembic/env.py`.

#### Decisiones tomadas

- **Los 25 atributos de `estrategia` conviven en una sola tabla.** Los bloques de métricas (Tabla 3.29) y escenarios (Tabla 3.30) son valores derivados pre-calculados externamente por el sistema que genera las estrategias, por lo que se almacenan como snapshot directamente en `estrategia`. Esto evita un `JOIN` extra en cada consulta del catálogo (alineado con el RNF-09: respuestas en menos de 2 s) y refleja fielmente cómo llegan los datos al backend.
- **Los campos de los bloques 2 y 3 son `nullable`.** Cuando un administrador crea una estrategia recién registrada todavía no hay datos ingeridos, por lo que esos campos quedan `NULL` hasta la primera ingesta.
- **`ON DELETE CASCADE`** en `resultado_estrategia → estrategia`: si se borra la estrategia padre, sus resultados históricos también desaparecen (son datos derivados sin valor por sí mismos).
- **`ON DELETE RESTRICT`** en las dos FKs de `contratacion`: borrar un usuario o una estrategia que tenga contrataciones es semánticamente sospechoso, así que la BBDD lo bloquea y fuerza al admin a cancelarlas explícitamente antes.
- **`CheckConstraint`** en `nivel_riesgo` para garantizar el rango 1..7 a nivel de BBDD, no solo en la capa Pydantic.

#### Pequeñas correcciones de nomenclatura frente al diseño teórico

Tres ajustes documentados para mantener trazabilidad con la memoria, sin desviarse del diseño:

| En la Tarea 2 | En código | Motivo |
|---|---|---|
| `comisión_ganancias` (con tilde) | `comision_ganancias` | Las tildes en nombres de columna PostgreSQL son muy problemáticas (obligan a entrecomillar siempre). |
| `ide_usuario` | `id_usuario` | Typo detectado en la Tabla 3.32. |
| `rol` con valor `'usuario'` (mi propuesta inicial) | `rol` con valor `'user'` | Respetar el diseño original de la Tabla 3.27. |

### Bloque 2 — Migración inicial con `--autogenerate`

#### Qué he hecho

- Generada la primera migración real con `alembic revision --autogenerate -m "crear entidades iniciales"`.
- Revisado el archivo generado a mano antes de aplicar, comprobando:
  - El orden de creación respeta las dependencias de FK (`estrategia` → `usuario` → `contratacion` → `resultado_estrategia`).
  - El `CheckConstraint` de `nivel_riesgo` aparece correctamente.
  - La PK compuesta de `resultado_estrategia` está bien declarada con su nombre explícito (`pk_resultado_estrategia`).
  - Las precisiones `Numeric` coinciden con las tablas de la memoria.
  - El `downgrade()` invierte el orden de creación correctamente.
- Aplicada con `alembic upgrade head` (hash `3f84bb494760`).
- Verificado en PostgreSQL: 5 tablas (4 nuevas + `alembic_version`), 3 tipos ENUM y los 8 índices esperados.

#### Incidencia detectada y resuelta — Valores ENUM en mayúsculas

Al revisar la primera versión de la migración detecté que SQLAlchemy generaba los tipos ENUM de PostgreSQL con los valores en **mayúsculas** (`'ACTIVA'`, `'PAUSADA'`, `'ADMIN'`, `'USER'`, `'CANCELADA'`) en lugar de en minúsculas como especifica el diseño de la Tarea 2 (Tablas 3.27, 3.28 y 3.32).

**Causa**: SQLAlchemy serializa por defecto el `NAME` de cada miembro de un Python `Enum`, no su `VALUE`. Con la declaración:

```python
class RolUsuario(str, Enum):
    ADMIN = "admin"  # NAME=ADMIN, VALUE="admin"
    USER = "user"
```

SQLAlchemy elegía el `NAME` (mayúsculas) para crear el tipo ENUM de PostgreSQL.

**Por qué importa**: el frontend y la API trabajan con JSON tipo `{"rol": "admin"}` (minúsculas, por convención REST). Si la BBDD esperase `"ADMIN"`, todas las inserciones fallarían en validación.

**Solución aplicada**: añadir `values_callable=lambda x: [e.value for e in x]` en las tres llamadas a `Enum(...)` de los modelos (`usuario.rol`, `estrategia.estado`, `contratacion.estado`). Eso fuerza a SQLAlchemy a usar el `VALUE` en lugar del `NAME`.

Tras el cambio, eliminé el archivo de migración incorrecto y regeneré con `alembic revision --autogenerate`. La nueva migración (hash `3f84bb494760`) usa los valores correctos en minúsculas, alineados con el diseño.

### Bloque 3 — Schemas Pydantic base

#### Qué he hecho

- Instalado el paquete `email-validator` (necesario para `EmailStr` de Pydantic v2) mediante `pip install "pydantic[email]==2.9.2"`. Añadido al `requirements.txt`.
- Creados 5 archivos en `backend/app/schemas/` siguiendo el patrón **Base / Create / Update / Read** por entidad:
  - `usuario.py` — con `EmailStr` para validar correo y password en plano para creación (nunca se expone `password_hash` en Read).
  - `estrategia.py` — `Base` con los 8 campos descriptivos; `Read` añade id, estado, timestamps y los 13 campos de métricas + escenarios como `Optional[Decimal]` (porque pueden ser `NULL` hasta la primera ingesta).
  - `resultado_estrategia.py` — con `drawdown` validado como `<= 0` mediante `Field(le=0)`.
  - `contratacion.py` — `Base` solo contiene `id_estrategia`; el `id_usuario` se extraerá del JWT en el endpoint, no del body, para evitar que un usuario contrate en nombre de otro.
- `app/schemas/__init__.py` reexporta todos los schemas agrupados por entidad.
- Sanity check con `python -c "from app.schemas import ..."` y arranque limpio del servidor uvicorn (sin errores de import).

#### Decisiones tomadas

- **Patrón Base/Create/Update/Read** consistente en las cuatro entidades, aunque `ResultadoEstrategia` y `Contratacion` no necesiten `Update` (los resultados se reemplazan por lotes desde la ingesta y las contrataciones solo se cancelan vía endpoint dedicado).
- **`from_attributes=True`** en todos los Read para poder construir el schema directamente desde objetos SQLAlchemy con `EstrategiaRead.model_validate(estrategia_orm)`.
- **Las métricas calculadas no se editan manualmente** desde `EstrategiaUpdate`. Solo el bloque descriptivo + estado son editables por API; el resto se rellena por ingesta.
- **`Field(..., description="...")`** en campos con validación, para que las descripciones aparezcan automáticamente en la documentación de Swagger UI.

### Evidencias del día

| Archivo | Contenido |
|---|---|
| `docs/evidencias/T3/13_migracion_aplicada.png` | Salida de `alembic upgrade head` con el hash de la migración. |
| `docs/evidencias/T3/14_tablas_creadas.png` | `\dt` mostrando las 5 tablas. |
| `docs/evidencias/T3/15_pk_compuesta.png` | `\d resultado_estrategia` con la PK compuesta y la FK CASCADE. |
| `docs/evidencias/T3/16_tipos_enum.png` | `\dT+` con los 3 ENUMs y sus valores en minúsculas. |
| `docs/evidencias/T3/17_alembic_current_post_upgrade.png` | `alembic current` indicando `3f84bb494760 (head)`. |
| `docs/evidencias/T3/18_modelos_directorio.png` | VS Code con `app/models/` y `estrategia.py` abiertos. |
| `docs/evidencias/T3/19_schemas_directorio.png` | VS Code con `app/schemas/` y `usuario.py` abiertos. |
| `docs/evidencias/T3/20_swagger_post_modelos.png` | Swagger UI con `/health` operativo tras los cambios del día. |

### Tiempo invertido

~4 h (≈1 h 30 min modelos + ≈1 h migración con incidencia ENUM + ≈1 h schemas + ≈30 min capturas, bitácora y commit). Dentro del rango previsto en el plan.

### Estado al cierre del día

Subtareas 3.5 y 3.6 cerradas. Mañana martes 12/05 entro en el **Bloque 3.3 + auth**: endpoints de registro y login, generación y validación de JWT, y las dependencias `get_current_user` / `require_admin` que protegerán el resto de endpoints.

---

## 2026-05-12 (Martes) — Subtarea 3.3 (auth): autenticación, JWT y dependencias

Jornada centrada en montar todo el sistema de autenticación y autorización del backend. Tres bloques encadenados: cimientos (utilidades de seguridad + dependencias), capa de aplicación (servicio + endpoints), y verificación end-to-end en Swagger.

### Bloque 1 — Módulos de seguridad (`security.py` + `deps.py`)

#### Qué he hecho

- Creado `app/core/security.py` con cuatro funciones puras: `hash_password`, `verify_password`, `create_access_token` y `decode_access_token`. Usa `passlib.context.CryptContext` con bcrypt para las contraseñas y `python-jose` para los JWT. El módulo no contiene lógica HTTP ni de negocio: solo primitivas reutilizables.
- Creado `app/core/deps.py` con las dependencias de FastAPI:
  - `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")` — la URL completa es importante para que Swagger UI sepa de dónde sacar el token al pulsar **Authorize**.
  - `get_current_user(token, db)` — decodifica el JWT, extrae el `sub` (id del usuario), lo busca en BBDD y devuelve el objeto `Usuario`. Lanza 401 si cualquier paso falla (token inválido, expirado, usuario inexistente).
  - `require_admin(current)` — encadena `get_current_user` y valida que `current.rol == RolUsuario.ADMIN`. Lanza 403 si no.
- Uso sistemático de `Annotated[..., Depends(...)]` como sintaxis moderna recomendada por FastAPI.

#### Decisiones tomadas

- **Almacenar el `id` del usuario como `sub` del JWT, no el correo.** El id es estable e inmutable; si en el futuro permitimos cambiar el correo, los tokens emitidos antes seguirían siendo válidos.
- **Token de 60 minutos** (`ACCESS_TOKEN_EXPIRE_MINUTES=60` en `config.py`). Es un equilibrio razonable: suficientemente largo para no interrumpir el trabajo del usuario, suficientemente corto para limitar el daño si el token se filtra. Para refresh tokens haría falta más infraestructura (almacén en BBDD, revocación, etc.); queda fuera del alcance del TFG.
- **HS256 como algoritmo de firma**. Simétrico, suficiente para un sistema con un solo servicio backend. Si en el futuro se separase en microservicios, habría que migrar a RS256 (asimétrico).
- **`get_current_user` consulta la BBDD en cada petición** en lugar de confiar solo en el payload del JWT. Penaliza un poco el rendimiento, pero garantiza que un usuario eliminado o deshabilitado pierde acceso inmediato, sin esperar a que su token expire.

### Bloque 2 — Servicio, router y registro en main

#### Qué he hecho

- Creado `app/services/usuario_service.py` con dos funciones:
  - `create_usuario(db, data)` — construye el objeto `Usuario`, hashea la contraseña con `hash_password`, intenta el commit. Si la BBDD devuelve `IntegrityError` por correo duplicado, hace `rollback` y lanza `ValueError("El correo ya está registrado")`. Devuelve el usuario refrescado.
  - `authenticate_usuario(db, correo, password)` — busca el usuario por correo, verifica la contraseña con `verify_password`, devuelve el `Usuario` si todo OK o `None` si no.
- Creado `app/routers/auth.py` con tres endpoints bajo el prefijo `/api/v1` y el tag `auth`:
  - `POST /users/register` — recibe `UsuarioCreate`, llama al servicio, devuelve `UsuarioRead` con código 201. Convierte `ValueError` en `HTTPException(400, ...)`.
  - `POST /auth/login` — usa `OAuth2PasswordRequestForm` como dependencia (form-data, no JSON; es el estándar OAuth2 y lo que Swagger UI espera nativamente). El campo `username` del formulario contiene el correo. Si las credenciales son válidas, devuelve `{access_token, token_type: "bearer"}`.
  - `GET /users/me` — endpoint mínimo de prueba que devuelve el usuario autenticado. Inyecta `get_current_user` como dependencia.
- Modificado `app/main.py` para registrar el nuevo router con `app.include_router(auth.router)`. No se ha tocado nada más del archivo.

#### Decisiones tomadas

- **El rol por defecto en el registro público es `user`.** No hay forma de crear un admin desde la API pública: los admins se crearán a mano por seed o por un script de bootstrap más adelante. Esto evita escaladas de privilegios accidentales.
- **El campo `username` del formulario OAuth2 contiene el correo.** Aunque el nombre del campo sea "username" por convención del estándar, semánticamente es nuestro identificador único (el correo). Documentado como comentario en el router.
- **La lógica de negocio vive en el servicio, no en el router.** El router solo orquesta: recibe entrada, llama al servicio, formatea salida. Esta separación se mantendrá en todos los routers que cree a partir de mañana (estrategias, contrataciones, etc.).

### Bloque 3 — Prueba end-to-end en Swagger UI

Verificadas en `/docs` las siete situaciones críticas del flujo de autenticación:

| Prueba | Resultado esperado | Resultado obtenido |
|---|---|---|
| 1. Registro con datos válidos | 201 + datos del usuario sin `password_hash` | ✅ |
| 2. Registro con correo duplicado | 400 + `"El correo ya está registrado"` | ✅ |
| 3. Login con credenciales válidas | 200 + `access_token` válido | ✅ |
| 4. `/users/me` sin autorización | 401 + `"Not authenticated"` | ✅ |
| 5. `/users/me` con token válido | 200 + datos del usuario autenticado | ✅ |
| 6. Login con contraseña incorrecta | 401 + `"Credenciales incorrectas"` | ✅ |
| 7. Verificación en BBDD del hash | `password_hash` con formato `$2b$12$...` (bcrypt) | ✅ |

Para la prueba 5, se usó el botón **Authorize** de Swagger UI, que llama internamente a `/api/v1/auth/login` con las credenciales introducidas y guarda el token devuelto para usarlo automáticamente en peticiones siguientes (cabecera `Authorization: Bearer <token>`).

### Conexión con el catálogo de la memoria

Lo implementado hoy cubre:

- **RF-01** (registro de usuarios), **RF-02** (autenticación) y **RF-03** (gestión de sesión basada en token).
- **RNF-01** (almacenamiento seguro de credenciales mediante hash) y **RNF-02** (autenticación basada en tokens firmados).
- **RNF-03** (control de acceso por roles) queda implementado en la dependencia `require_admin`, aunque su primer uso real en endpoints será mañana, al proteger el CRUD de estrategias.
- **DA-02** (driver de autenticación) y **DA-03** (driver de autorización por roles) del capítulo 3 de la memoria.

### Evidencias del día

| Archivo | Contenido |
|---|---|
| `docs/evidencias/T3/21_swagger_auth_endpoints.png` | Swagger UI con los 3 endpoints nuevos bajo el tag `auth`. |
| `docs/evidencias/T3/22_register_201.png` | `POST /users/register` → 201 con datos sin `password_hash`. |
| `docs/evidencias/T3/23_register_duplicado_400.png` | Registro duplicado → 400. |
| `docs/evidencias/T3/24_login_token.png` | `POST /auth/login` → 200 con `access_token`. |
| `docs/evidencias/T3/25_me_sin_token_401.png` | `/users/me` sin autorización → 401. |
| `docs/evidencias/T3/26_me_con_token_200.png` | `/users/me` con token → 200 con datos del usuario. |
| `docs/evidencias/T3/27_login_password_erroneo_401.png` | Login con contraseña incorrecta → 401. |
| `docs/evidencias/T3/28_usuario_en_bbdd.png` | Fila del usuario en `psql` con `password_hash` en formato bcrypt. |

### Tiempo invertido

~3 h 30 min (≈45 min cimientos + ≈1 h capa de aplicación + ≈45 min pruebas y capturas + ≈30 min commit y bitácora).

### Estado al cierre del día

Subtarea 3.3 (auth) cerrada. El sistema de autenticación está operativo y verificado end-to-end. Mañana miércoles 13/05 entra el **CRUD completo de estrategias protegido por rol admin**, que será la primera aplicación real de la dependencia `require_admin` en endpoints reales.


## Miércoles 13/05/2026 — Bloque 3.3 (CRUD de estrategias)

### Objetivo del día
Implementar el CRUD completo de la entidad estrategia con endpoints
de escritura restringidos a rol admin y endpoints de lectura públicos.
Incluir borrado lógico (*soft delete*) que cancele en cascada las
contrataciones activas y devuelva el dinero invertido al monedero
del usuario propietario.

### Decisiones de diseño
1. **Visibilidad de los GET pública.** Tanto el catálogo (`GET
   /api/v1/estrategias`) como el detalle (`GET /api/v1/estrategias/{id}`)
   son accesibles sin autenticación, reflejando el modelo habitual de
   plataformas de inversión donde un visitante explora la oferta antes
   de registrarse.
2. **Introducción del monedero del usuario.** Cada usuario dispone de
   un campo `saldo_monedero` (Decimal 12,2) con valor inicial 10.000 €
   al registrarse. Decisión añadida hoy fuera del plan original; obliga
   a actualizar el documento de Tarea 2 (Análisis y Diseño) antes del
   cierre de la Tarea 3.
3. **Soft delete con devolución automática.** El endpoint DELETE no
   borra físicamente la estrategia, sino que pone `activa = False`,
   cancela todas las contrataciones activas y devuelve el
   `monto_invertido` de cada una al `saldo_monedero` del usuario
   correspondiente, todo en una transacción atómica.
4. **PATCH en lugar de PUT.** Dada la elevada cardinalidad de
   atributos de la entidad estrategia (26 columnas), las
   actualizaciones se realizan vía PATCH con `exclude_unset=True`
   para evitar que omitir un campo signifique borrarlo.
5. **Ubicación temporal de la lógica de cancelación.** La cancelación
   de contrataciones reside provisionalmente en `estrategia_service`;
   se extraerá mañana al nuevo `contratacion_service` cuando se
   implementen los endpoints de contratación por parte del usuario.

### Cambios realizados
- **Modelos (`app/models/`):**
  - `usuario.Usuario`: nuevo campo `saldo_monedero` Numeric(12,2).
  - `estrategia.Estrategia`: nuevo campo `activa` Boolean.
  - `contratacion.Contratacion`: nuevo campo `monto_invertido`
    Numeric(12,2).
- **Migración Alembic `bc3f4b90342a`.** Aplicada con un ajuste manual:
  `server_default=sa.text("10000.00")` en la columna `saldo_monedero`
  para que las filas existentes de `usuario` recibieran el valor por
  defecto sin violar el NOT NULL.
- **Schemas (`app/schemas/`):** `UsuarioRead` expone `saldo_monedero`;
  `EstrategiaRead` expone `activa`. Se corrigió `EstrategiaCreate`
  eliminando los campos `id`, `fecha_creacion`, `fecha_ult_actualizacion`
  y `activa`, que no deben ser proporcionados por el cliente.
- **Servicio `app/services/estrategia_service.py`** (nuevo). Cinco
  funciones síncronas, HTTP-agnósticas: `crear_estrategia`,
  `listar_estrategias`, `obtener_estrategia_por_id`,
  `actualizar_estrategia`, `dar_de_baja_estrategia`. Comunica errores
  mediante `None` (no encontrado) y `ValueError` (conflictos de
  unicidad).
- **Router `app/routers/estrategias.py`** (nuevo). Cinco endpoints:
  - `POST /api/v1/estrategias` — admin — crea estrategia (201).
  - `GET /api/v1/estrategias` — público — lista solo estrategias activas.
  - `GET /api/v1/estrategias/{id}` — público — detalle solo si está activa.
  - `PATCH /api/v1/estrategias/{id}` — admin — actualización parcial.
  - `DELETE /api/v1/estrategias/{id}` — admin — soft delete con cascada.
  Los endpoints traducen `None → 404` y `ValueError → 409`.
- **`app/main.py`:** registro del nuevo router bajo el prefijo
  `/api/v1`.

### Pruebas ejecutadas (Swagger)
1. POST con body válido → 201 Created. La estrategia aparece con
   `activa: true` y `id` asignado por la secuencia de la BBDD.
2. GET del catálogo público (sin token) → 200 con la estrategia
   listada.
3. GET de detalle por id (sin token) → 200 con todos los campos.
4. POST con nombre duplicado → 409 Conflict con mensaje descriptivo.
5. PATCH modificando un único campo → 200 OK con el campo actualizado
   y el resto intactos.
6. DELETE con admin → 200 OK con la estrategia mostrando
   `activa: false`.
7. GET tras DELETE → catálogo vacío + 404 al consultar por id.
8. Verificación en BBDD: `SELECT id, nombre, activa FROM estrategia;`
   confirma que la fila se conserva con `activa = false`.

### Incidencias y resoluciones
- **Migración percibida como incompleta inicialmente.** La primera
  generación con `--autogenerate` solo detectó `monto_invertido` para
  `contratacion`. Investigación: los campos `estado`, `fecha_cancelacion`
  y el enum `EstadoContratacion` ya existían en el modelo desde el
  lunes; el comportamiento de Alembic era correcto.
- **Error 403 al probar POST.** Causa: usuario de prueba con rol
  `user`. Resolución: promoción manual mediante
  `UPDATE usuario SET rol = 'admin' WHERE correo = 'admin@test.com'`.
  Decisión consciente: el endpoint de registro no permite asignarse
  rol admin (correcto por seguridad); el primer admin se promueve en
  BBDD o por seed.
- **Esquema `EstrategiaCreate` con campos no controlados por el
  cliente.** Detectado al revisar el Example Value en Swagger.
  Corregido eliminando `id`, `fecha_creacion`, `fecha_ult_actualizacion`
  y `activa` del schema.

### Cambios pendientes en `T2_Analisis_y_Diseno.docx`
Bloque a realizar antes del cierre de la Tarea 3 (planificado para
el viernes/sábado):
- 4-5 RFs nuevos sobre el monedero (saldo inicial al registrarse,
  consulta del saldo, validación de saldo suficiente al contratar,
  devolución al cancelar contratación, devolución al dar de baja
  una estrategia).
- 1 RF nuevo sobre soft delete de estrategias con cascada.
- Modificación del RF de contratación existente para incluir la
  precondición de saldo.
- Atributos nuevos en el diagrama ER: `usuario.saldo_monedero`,
  `estrategia.activa`, `contratacion.monto_invertido`,
  `contratacion.estado`, `contratacion.fecha_cancelacion`.
- 1-2 CUs nuevos (consulta del saldo, baja de estrategia con cascada).
- Regeneración de la matriz de trazabilidad RF→CU.

### Trabajo futuro identificado (para conclusiones / mejoras)
- El método `dar_de_baja_estrategia` presenta patrón N+1 al cargar
  el usuario propietario de cada contratación. Optimizable mediante
  `selectinload` o `UPDATE` masivo si la operación se ejecuta sobre
  estrategias con muchas suscripciones.
- El endpoint DELETE podría devolver un resumen de la cascada
  (nº de contrataciones canceladas, monto total devuelto) para
  mejorar el feedback al admin.
- Se podría añadir un endpoint de reactivación de estrategias
  (`PATCH /{id}/reactivar`) que ponga `activa = True`, completando
  el ciclo de vida del borrado lógico.

### Capturas
T3_29 a T3_41 en `docs/evidencias/T3/`.

### Próximo día (jueves 14/05)
Bloque 3.3 catálogo + contrataciones: endpoints públicos de catálogo
ya hechos, falta implementar `POST /contrataciones` (contratar) y
`PATCH /contrataciones/{id}/cancelar` (cancelar por usuario).
Extracción de la lógica de cancelación a `contratacion_service`.