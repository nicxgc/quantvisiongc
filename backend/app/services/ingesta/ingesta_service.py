"""Servicio orquestador de ingesta de paquetes.

Flujo principal
---------------
1.  Verificar que los bytes recibidos son un ZIP válido.
2.  Extraer el ZIP a un directorio temporal y localizar los tres xlsx
    (búsqueda case-insensitive).
3.  Validar strategies.xlsx  → si hay errores bloqueantes, abortar.
4.  Validar metrics_summary.xlsx → si hay errores bloqueantes, abortar.
5.  Validar equity_curves.xlsx   → si hay errores bloqueantes, abortar.
6.  Persistir los tres conjuntos de datos en BD (transacción única).
7.  Devolver (summary_dict, warnings) o (None, errores_bloqueantes).

El directorio temporal se destruye al salir del bloque ``with``, por lo
que no deja ficheros huérfanos en disco incluso si la validación falla.
"""

from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

from sqlalchemy.orm import Session

from sqlalchemy.exc import IntegrityError as SAIntegrityError

from app.services.ingesta.errors import IngestaError
from app.services.ingesta.persistencia import PersistenciaError, persistir_paquete
from app.services.ingesta.validador_equity import validar_equity_curves
from app.services.ingesta.validador_metrics import validar_metrics_summary
from app.services.ingesta.validador_strategies import validar_strategies

# Nombres de los tres archivos que deben existir dentro del ZIP.
# Se comparan en minúsculas para tolerar diferencias de capitalización.
_ARCHIVOS_REQUERIDOS: frozenset[str] = frozenset(
    {"strategies.xlsx", "metrics_summary.xlsx", "equity_curves.xlsx"}
)


# ─────────────────────────────────────────────────────────────────────────────
# Función pública
# ─────────────────────────────────────────────────────────────────────────────

def ingestar_paquete(
    zip_bytes: bytes,
    db: Session,
) -> tuple[dict | None, list[IngestaError]]:
    """Descomprime el ZIP, valida los tres xlsx y persiste los datos en BD.

    Parámetros
    ----------
    zip_bytes : bytes
        Contenido binario del fichero ZIP recibido por la API.
    db : Session
        Sesión SQLAlchemy abierta por el router (autocommit=False).

    Devuelve
    --------
    (summary_dict, warnings)
        Si la ingesta termina con éxito.  ``summary_dict`` tiene las claves
        ``estrategias_creadas``, ``metricas_creadas``, ``resultados_creados``.
        ``warnings`` es la lista de IngestaError con nivel='warning'.
    (None, errores)
        Si algún validador lanzó errores bloqueantes o falló la persistencia.
        ``errores`` incluye todos los IngestaError recopilados hasta el punto
        de fallo.
    """
    errores: list[IngestaError] = []

    # ── 1. Verificar que es un ZIP válido ──────────────────────────────────
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except (zipfile.BadZipFile, Exception):
        errores.append(
            IngestaError(
                archivo="paquete.zip",
                codigo="ZIP_INVALID",
                mensaje="El archivo no es un ZIP válido o está corrupto.",
            )
        )
        return None, errores

    # ── 2. Extraer y localizar los xlsx ────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        zf.extractall(tmpdir)
        zf.close()

        tmppath = Path(tmpdir)

        # Mapa nombre_lower → ruta absoluta (ignora mayúsculas)
        lower_map: dict[str, Path] = {
            f.name.lower(): f
            for f in tmppath.rglob("*")
            if f.is_file()
        }

        rutas: dict[str, Path | None] = {
            nombre: lower_map.get(nombre) for nombre in _ARCHIVOS_REQUERIDOS
        }

        faltantes = sorted(n for n, p in rutas.items() if p is None)
        if faltantes:
            errores.append(
                IngestaError(
                    archivo="paquete.zip",
                    codigo="ZIP_INCOMPLETE",
                    mensaje=(
                        f"Faltan archivos en el ZIP: {', '.join(faltantes)}. "
                        "El paquete debe contener strategies.xlsx, "
                        "metrics_summary.xlsx y equity_curves.xlsx."
                    ),
                )
            )
            return None, errores

        # ── 3. Validar strategies ──────────────────────────────────────────
        strats, s_errs = validar_strategies(rutas["strategies.xlsx"])
        errores.extend(s_errs)
        if any(e.nivel == "error" for e in s_errs):
            return None, errores

        # ── 4. Validar metrics ─────────────────────────────────────────────
        metrics, m_errs = validar_metrics_summary(
            rutas["metrics_summary.xlsx"], strats
        )
        errores.extend(m_errs)
        if any(e.nivel == "error" for e in m_errs):
            return None, errores

        # ── 5. Validar equity ──────────────────────────────────────────────
        equity, e_errs = validar_equity_curves(
            rutas["equity_curves.xlsx"], strats, metrics
        )
        errores.extend(e_errs)
        if any(e.nivel == "error" for e in e_errs):
            return None, errores

    # El TemporaryDirectory ya se destruyó aquí; las listas strats/metrics/equity
    # contienen únicamente datos Python (dicts), sin referencias al disco.

    # ── 6. Persistir en BD ─────────────────────────────────────────────────
    try:
        summary = persistir_paquete(db, strats, metrics, equity)
    except PersistenciaError as exc:
        # Cualquier IntegrityError subyacente al reintentar la misma ingesta
        # indica que los datos ya existen en BD (alguna restricción UNIQUE violada).
        es_duplicado = isinstance(getattr(exc, "causa", None), SAIntegrityError)
        errores.append(
            IngestaError(
                archivo="paquete.zip",
                codigo="CONFLICT_DUPLICATE" if es_duplicado else "DB_ERROR",
                mensaje=str(exc),
            )
        )
        return None, errores

    # Solo warnings llegan aquí
    warnings = [e for e in errores if e.nivel == "warning"]
    return summary, warnings
