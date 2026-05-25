"""Capa de persistencia para el módulo de ingesta de paquetes.

Expone una única función pública ``persistir_paquete`` que recibe los datos
ya validados por los tres validadores y los persiste en BD dentro de una
única transacción atómica.

Flujo de persistencia
---------------------
1.  Calcular retorno_total por (id_estrategia, periodo) a partir de la serie
    temporal de equity (primer y último valor de cada grupo).
2.  INSERT masivo de Estrategia (ORM, con flush para obtener IDs autogenerados).
3.  Construir mapping  codigo_estrategia → id_db  y enriquecer los dicts de
    métricas con el id entero y el retorno_total calculado.
4.  Bulk INSERT de MetricaEstrategia usando execute(insert(...), list_of_dicts).
5.  Transformar equity_data (id string → id int) y hacer Bulk INSERT de
    ResultadoEstrategia en bloques de _CHUNK_SIZE filas.
6.  db.commit().

Si cualquier paso lanza una excepción, se hace db.rollback() y se relanza como
PersistenciaError para que el servicio orquestador la convierta en respuesta HTTP.

Nota sobre retorno_total
------------------------
La columna metrica_estrategia.retorno_total (NOT NULL) no está en el xlsx de
métricas.  Se calcula aquí como:

    retorno_total = (equity_final / equity_inicial) - 1

usando el primer y último punto de la serie temporal de equity de cada grupo
(id_estrategia, periodo).  El equity inicial es siempre 100 000 (normalizado),
por lo que la fórmula es equivalente a  equity_final / 100 000 - 1.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import insert, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.estrategia import EstadoEstrategia, Estrategia
from app.models.metrica_estrategia import MetricaEstrategia
from app.models.resultado_estrategia import ResultadoEstrategia
from app.services.ingesta.defaults import (
    calcular_comision_ganancias,
    calcular_precio_subscripcion,
)

# Filas por bloque en el INSERT masivo de resultado_estrategia.
# 10 000 filas × ≈80 bytes/fila ≈ 800 kB por bloque — mantenible en memoria
# y lo suficientemente grande para aprovechar el batching de psycopg3.
_CHUNK_SIZE = 10_000


# ─────────────────────────────────────────────────────────────────────────────
# Excepción de dominio
# ─────────────────────────────────────────────────────────────────────────────

class PersistenciaError(Exception):
    """Señala un fallo en la capa de persistencia durante la ingesta."""

    def __init__(self, mensaje: str, causa: Exception | None = None) -> None:
        super().__init__(mensaje)
        self.causa = causa


# ─────────────────────────────────────────────────────────────────────────────
# Función pública
# ─────────────────────────────────────────────────────────────────────────────

def persistir_paquete(
    db: Session,
    strategies_data: list[dict],
    metrics_data: list[dict],
    equity_data: list[dict],
) -> dict[str, int]:
    """Persiste el paquete validado en BD dentro de una única transacción.

    Parámetros
    ----------
    db : Session
        Sesión SQLAlchemy abierta por el router (autocommit=False).
    strategies_data : list[dict]
        Output de ``validar_strategies`` — 32 dicts.
    metrics_data : list[dict]
        Output de ``validar_metrics_summary`` — 64 dicts.
    equity_data : list[dict]
        Output de ``validar_equity_curves`` — ≈137 000 dicts.

    Devuelve
    --------
    dict con claves estrategias_creadas, metricas_creadas, resultados_creados.

    Lanza
    -----
    PersistenciaError
        Si hay un IntegrityError (p.ej. codigo_estrategia duplicado) u otro
        fallo de BD.  La transacción es revertida antes de lanzar la excepción.
    """
    try:
        # ── 1. retorno_total por (id_estrategia_str, periodo) ─────────────────
        retorno_total_map = _compute_retorno_total(equity_data)

        # ── 2. INSERT Estrategia (ORM) + flush para obtener IDs ───────────────
        orm_objs: list[Estrategia] = []
        for s in strategies_data:
            precio = calcular_precio_subscripcion(s["tipo"], s["nivel_riesgo"])
            comision = calcular_comision_ganancias(s["tipo"])
            obj = Estrategia(
                codigo_estrategia     = s["id"],
                nombre                = s["nombre"],
                descripcion           = s.get("descripcion"),
                tipo_activo           = s["tipo_activo"],
                tipo                  = s["tipo"],
                categoria             = s["categoria"],
                nivel_riesgo          = s["nivel_riesgo"],
                precio_subscripcion   = precio,
                comision_ganancias    = comision,
                fecha_inicio          = s["fecha_inicio"],
                fecha_fin             = s.get("fecha_fin"),
                estado                = EstadoEstrategia.ACTIVA,
                activa                = True,
            )
            db.add(obj)
            orm_objs.append(obj)

        db.flush()   # dispara INSERTs → autoincrement IDs quedan en orm_objs

        # Mapping código-legible → id entero de BD
        codigo_to_id: dict[str, int] = {
            obj.codigo_estrategia: obj.id for obj in orm_objs
        }

        # ── 3. Bulk INSERT MetricaEstrategia ──────────────────────────────────
        metrics_rows: list[dict[str, Any]] = [
            {
                "id_estrategia":      codigo_to_id[m["id_estrategia"]],
                "periodo":            m["periodo"],
                "fecha_inicio_periodo": m["fecha_inicio_periodo"],
                "fecha_fin_periodo":  m["fecha_fin_periodo"],
                "retorno_total":      retorno_total_map.get(
                                          (m["id_estrategia"], m["periodo"]),
                                          Decimal("0.0000"),
                                      ),
                "cagr":               m["cagr"],
                "volatility":         m["volatility"],
                "sharpe":             m["sharpe"],
                "sortino":            m["sortino"],
                "calmar":             m["calmar"],
                "mdd":                m["mdd"],
                "n_trades":           m.get("n_trades"),
                "hit_rate":           m.get("hit_rate"),
                "profit_factor":      m.get("profit_factor"),
            }
            for m in metrics_data
        ]
        db.execute(insert(MetricaEstrategia), metrics_rows)

        # ── 4. Bulk INSERT ResultadoEstrategia (chunked) ──────────────────────
        equity_rows: list[dict[str, Any]] = [
            {
                "id_estrategia": codigo_to_id[e["id_estrategia"]],
                "periodo":       e["periodo"],
                "fecha":         e["fecha"],
                "equity":        e["equity"],
                "drawdown":      e["drawdown"],
                "retorno":       e["retorno"],
            }
            for e in equity_data
        ]

        n_total = len(equity_rows)
        for start in range(0, n_total, _CHUNK_SIZE):
            chunk = equity_rows[start : start + _CHUNK_SIZE]
            db.execute(insert(ResultadoEstrategia), chunk)

        # ── 5. Commit ─────────────────────────────────────────────────────────
        db.commit()

        return {
            "estrategias_creadas": len(strategies_data),
            "metricas_creadas":    len(metrics_data),
            "resultados_creados":  n_total,
        }

    except IntegrityError as exc:
        db.rollback()
        msg = str(exc.orig) if exc.orig else str(exc)
        # Detectar violación UNIQUE en codigo_estrategia
        if "uq_estrategia_codigo_estrategia" in msg or "codigo_estrategia" in msg:
            raise PersistenciaError(
                "Ya existe una estrategia con ese codigo_estrategia en BD. "
                "Limpia la base de datos antes de re-ingerir el paquete.",
                causa=exc,
            ) from exc
        raise PersistenciaError(
            f"Error de integridad en BD: {msg}",
            causa=exc,
        ) from exc

    except Exception as exc:
        db.rollback()
        raise PersistenciaError(
            f"Error inesperado durante la persistencia: {exc}",
            causa=exc,
        ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# Helpers privados
# ─────────────────────────────────────────────────────────────────────────────

def _compute_retorno_total(
    equity_data: list[dict],
) -> dict[tuple[str, str], Decimal]:
    """Calcula retorno_total por (id_estrategia_str, periodo) a partir de la
    serie temporal de equity.

    retorno_total = (equity_final / equity_inicial) - 1

    La serie debe estar ordenada (los validadores la garantizan).  Si por
    alguna razón el grupo tiene menos de 2 puntos, retorna Decimal('0.0000').
    """
    groups: dict[tuple[str, str], list[tuple[object, float]]] = defaultdict(list)
    for row in equity_data:
        key = (row["id_estrategia"], row["periodo"])
        groups[key].append((row["fecha"], float(row["equity"])))

    result: dict[tuple[str, str], Decimal] = {}
    for key, rows in groups.items():
        if len(rows) < 2:
            result[key] = Decimal("0.0000")
            continue
        rows.sort(key=lambda x: x[0])   # ordenar por fecha
        first_eq = rows[0][1]
        last_eq  = rows[-1][1]
        if first_eq == 0:
            result[key] = Decimal("0.0000")
        else:
            rt = round((last_eq / first_eq - 1), 4)
            result[key] = Decimal(str(rt))

    return result
