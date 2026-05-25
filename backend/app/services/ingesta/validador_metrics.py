"""Validador estricto para el archivo metrics_summary.xlsx del paquete de ingesta.

Realiza la validación en tres niveles antes de devolver datos listos para BD:

  Nivel 1 — Estructural (aborta si falla):
    a) El archivo existe y es un xlsx válido.
    b) Tiene al menos 1 fila de datos (FILE_EMPTY).
    c) Tiene exactamente las 13 columnas requeridas (COL_MISSING bloqueante;
       COL_UNEXPECTED no bloqueante).
    d) Tiene 64 filas (WARN_ROW_COUNT, no bloqueante).

  Nivel 2 — Por celda (recorre TODAS las filas, acumula errores):
    e) Celdas obligatorias no nulas: id_estrategia, periodo, fecha_inicio_periodo,
       fecha_fin_periodo, cagr, volatility, sharpe, sortino, calmar, mdd.
    f) Parsing de tipos: fechas → date, métricas float → Decimal (4 dec.), n_trades → int.
    g) Enum periodo en {'dev', 'oos'} (ENUM_INVALID).
    h) Rangos numéricos (RANGE_INVALID):
         cagr       ∈ [-5, 5]
         volatility ∈ (0, 5]    (estrictamente positiva)
         sharpe     ∈ [-10, 10]
         sortino    ∈ [-10, 10]
         calmar     ∈ [-50, 50]
         mdd        ∈ [-1, 0]
         hit_rate   ∈ [0, 1]    (cuando no es NULL)
         profit_f.  ∈ (0, 10]   (cuando no es NULL)
         n_trades   ∈ [0, 100000] (cuando no es NULL)
    i) WARN_CALMAR (warning): abs(calmar − cagr/|mdd|) >= 0.01.
       Se omite si mdd ≈ 0.

  Nivel 3 — Referencial y cruzada (post-loop, cross-row / cross-column):
    j)  REF_NOT_FOUND: id_estrategia debe existir en strategies_validas.
    k)  ROW_COUNT_PER_STRATEGY: cada estrategia debe tener exactamente 1 fila
        'dev' y 1 fila 'oos'.
    l)  DATE_INVALID por fila: fecha_fin_periodo >= fecha_inicio_periodo.
    m)  DATE_RANGE_OUT: las fechas del periodo deben estar contenidas en
        [estrategia.fecha_inicio, estrategia.fecha_fin].
    n)  DATE_OVERLAP: oos.fecha_inicio_periodo debe ser estrictamente posterior
        al dev.fecha_fin_periodo (se admite contigüidad, no solapamiento).
    o)  CONSTRAINT_CROSS (NULL_CONDITIONAL):
          benchmark       → n_trades, hit_rate, profit_factor DEBEN ser NULL.
          estrategia_activa → n_trades, hit_rate, profit_factor DEBEN ser NOT NULL.

CONVENCIÓN DE INDEXACIÓN DE FILAS
----------------------------------
Las filas se reportan 1-indexed contando la cabecera como fila 1.
La primera fila de datos es la fila 2, que coincide con la fila 2 en Excel.

CONVERSIÓN DECIMAL
------------------
Los floats de pandas se convierten a Decimal usando:
    Decimal(str(round(float(val), 4)))
Esto preserva 4 decimales de precisión coherentes con NUMERIC(10,4) en BD
y evita representaciones inexactas de binario flotante.

CONTRATO DE RETORNO
-------------------
    datos, errores = validar_metrics_summary(ruta, strategies_validas)

  - Si hay errores bloqueantes (nivel='error'):  datos = [],    errores = [...]
  - Solo advertencias (nivel='warning'):          datos = [...], errores = [advertencias]
  - Sin ningún problema:                          datos = [...], errores = []

  Cada dict en `datos` contiene:
    id_estrategia (str), periodo (str),
    fecha_inicio_periodo (date), fecha_fin_periodo (date),
    n_trades (int | None),
    cagr (Decimal), volatility (Decimal), sharpe (Decimal),
    sortino (Decimal), calmar (Decimal), mdd (Decimal),
    hit_rate (Decimal | None), profit_factor (Decimal | None)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

import pandas as pd

from app.services.ingesta.errors import IngestaError

# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────

_ARCHIVO = "metrics_summary.xlsx"
_FILAS_ESPERADAS = 64

_COLUMNAS_ESPERADAS: list[str] = [
    "id_estrategia", "periodo",
    "fecha_inicio_periodo", "fecha_fin_periodo",
    "n_trades", "cagr", "volatility", "sharpe",
    "sortino", "calmar", "mdd",
    "hit_rate", "profit_factor",
]

_PERIODO_VALS: frozenset[str] = frozenset({"dev", "oos"})

# (nombre_columna, min_incl, max_incl, min_exclusivo)
#   min_exclusivo=True → el mínimo es estrictamente mayor que rng_min
_METRICAS_OBLIG: list[tuple[str, float, float, bool]] = [
    ("cagr",       -5.0,   5.0,  False),
    ("volatility",  0.0,   5.0,  True ),   # > 0
    ("sharpe",    -10.0,  10.0,  False),
    ("sortino",   -10.0,  10.0,  False),
    ("calmar",    -50.0,  50.0,  False),
    ("mdd",        -1.0,   0.0,  False),
]


# ─────────────────────────────────────────────────────────────────────────────
# Función pública
# ─────────────────────────────────────────────────────────────────────────────

def validar_metrics_summary(
    ruta_xlsx: Path,
    strategies_validas: list[dict],
) -> tuple[list[dict], list[IngestaError]]:
    """Valida metrics_summary.xlsx y devuelve los datos parseados o la lista de errores.

    Parámetros
    ----------
    ruta_xlsx : Path
        Ruta absoluta al archivo metrics_summary.xlsx.
    strategies_validas : list[dict]
        Output de ``validar_strategies`` — lista de dicts con claves:
        'id', 'tipo', 'fecha_inicio' (date), 'fecha_fin' (date), …
        Se usa para validar referencias y restricciones relacionales.

    Ver docstring de módulo para el contrato completo y la convención de filas.
    """
    errores: list[IngestaError] = []

    # Lookup O(1) por id de estrategia
    strat_by_id: dict[str, dict] = {s["id"]: s for s in strategies_validas}

    # ── Nivel 1a: El archivo existe ───────────────────────────────────────────
    if not ruta_xlsx.exists():
        errores.append(_e("FILE_MISSING", f"Archivo no encontrado: {ruta_xlsx}"))
        return [], errores

    # ── Nivel 1a: Archivo legible como xlsx ───────────────────────────────────
    try:
        df = pd.read_excel(ruta_xlsx, dtype=str, keep_default_na=True)
    except Exception as exc:
        errores.append(_e("FILE_INVALID", f"No se pudo leer el archivo como xlsx: {exc}"))
        return [], errores

    # ── Nivel 1b: Al menos 1 fila de datos ───────────────────────────────────
    if len(df) == 0:
        errores.append(_e("FILE_EMPTY", "El archivo no contiene filas de datos."))
        return [], errores

    # ── Nivel 1c: Columnas requeridas presentes ───────────────────────────────
    cols_presentes = set(df.columns)
    cols_esperadas = set(_COLUMNAS_ESPERADAS)

    for col in sorted(cols_esperadas - cols_presentes):
        errores.append(_e(
            "COL_MISSING",
            f"Columna requerida '{col}' no encontrada en el archivo.",
            columna=col,
        ))

    for col in sorted(cols_presentes - cols_esperadas):
        errores.append(_e(
            "COL_UNEXPECTED",
            f"Columna inesperada '{col}' presente en el archivo. Se ignorará.",
            columna=col,
            nivel="warning",
        ))

    if any(e.codigo == "COL_MISSING" for e in errores):
        return [], errores

    # ── Nivel 1d: Conteo de filas (no bloqueante) ─────────────────────────────
    if len(df) != _FILAS_ESPERADAS:
        errores.append(_e(
            "WARN_ROW_COUNT",
            f"Se esperaban {_FILAS_ESPERADAS} filas de datos, "
            f"se encontraron {len(df)}. Verificar que el archivo está completo.",
            nivel="warning",
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # Niveles 2 y 3 (in-loop): por fila, acumula sin abortar
    # ─────────────────────────────────────────────────────────────────────────

    datos_parciales: list[dict] = []
    fila_ok_flags: list[bool] = []

    # Agrupador para checks cross-row posteriores
    # rows_by_strat[id_strat] = list of (df_idx, parsed, fila_excel)
    rows_by_strat: dict[str, list[tuple[int, dict, int]]] = defaultdict(list)

    for df_idx, row in df.iterrows():
        fila_excel = int(df_idx) + 2   # cabecera=fila 1, primer dato=fila 2
        fila_ok = True
        parsed: dict = {}

        # ── id_estrategia ─────────────────────────────────────────────────────
        id_raw = row.get("id_estrategia")
        if _vacio(id_raw):
            errores.append(_ef(fila_excel, "id_estrategia", "TYPE_INVALID",
                               "El campo 'id_estrategia' no puede estar vacío."))
            fila_ok = False
        else:
            parsed["id_estrategia"] = str(id_raw).strip()

        # ── periodo ───────────────────────────────────────────────────────────
        per_raw = row.get("periodo")
        if _vacio(per_raw):
            errores.append(_ef(fila_excel, "periodo", "TYPE_INVALID",
                               "El campo 'periodo' no puede estar vacío."))
            fila_ok = False
        else:
            per_str = str(per_raw).strip()
            if per_str not in _PERIODO_VALS:
                errores.append(_ef(fila_excel, "periodo", "ENUM_INVALID",
                                   f"Valor '{per_str}' no permitido en 'periodo'. "
                                   f"Valores válidos: {sorted(_PERIODO_VALS)}."))
                fila_ok = False
            else:
                parsed["periodo"] = per_str

        # ── fecha_inicio_periodo ──────────────────────────────────────────────
        fi_raw = row.get("fecha_inicio_periodo")
        if _vacio(fi_raw):
            errores.append(_ef(fila_excel, "fecha_inicio_periodo", "TYPE_INVALID",
                               "El campo 'fecha_inicio_periodo' no puede estar vacío."))
            fila_ok = False
        else:
            try:
                parsed["fecha_inicio_periodo"] = date.fromisoformat(str(fi_raw).strip())
            except ValueError:
                errores.append(_ef(fila_excel, "fecha_inicio_periodo", "DATE_INVALID",
                                   f"Formato de fecha inválido '{fi_raw}'. Se espera YYYY-MM-DD."))
                fila_ok = False

        # ── fecha_fin_periodo ─────────────────────────────────────────────────
        ff_raw = row.get("fecha_fin_periodo")
        if _vacio(ff_raw):
            errores.append(_ef(fila_excel, "fecha_fin_periodo", "TYPE_INVALID",
                               "El campo 'fecha_fin_periodo' no puede estar vacío."))
            fila_ok = False
        else:
            try:
                parsed["fecha_fin_periodo"] = date.fromisoformat(str(ff_raw).strip())
            except ValueError:
                errores.append(_ef(fila_excel, "fecha_fin_periodo", "DATE_INVALID",
                                   f"Formato de fecha inválido '{ff_raw}'. Se espera YYYY-MM-DD."))
                fila_ok = False

        # ── Métricas obligatorias (float → Decimal) ───────────────────────────
        for col_name, rng_min, rng_max, excl_min in _METRICAS_OBLIG:
            raw = row.get(col_name)
            if _vacio(raw):
                errores.append(_ef(fila_excel, col_name, "TYPE_INVALID",
                                   f"El campo '{col_name}' no puede estar vacío."))
                fila_ok = False
            else:
                try:
                    fval = float(str(raw).strip())
                    fuera = fval <= rng_min if excl_min else fval < rng_min
                    if fuera or fval > rng_max:
                        sep = "(" if excl_min else "["
                        errores.append(_ef(fila_excel, col_name, "RANGE_INVALID",
                                           f"Valor {fval:.6g} fuera del rango permitido "
                                           f"{sep}{rng_min}, {rng_max}]."))
                        fila_ok = False
                    else:
                        parsed[col_name] = _to_decimal(fval)
                except (ValueError, TypeError) as exc:
                    errores.append(_ef(fila_excel, col_name, "TYPE_INVALID",
                                       f"Valor '{raw}' no es un número válido: {exc}"))
                    fila_ok = False

        # ── n_trades (int opcional) ───────────────────────────────────────────
        nt_raw = row.get("n_trades")
        if _vacio(nt_raw):
            parsed["n_trades"] = None
        else:
            try:
                nt_f = float(str(nt_raw).strip())
                if nt_f != int(nt_f):
                    raise ValueError("n_trades debe ser un entero (sin parte decimal).")
                nt_i = int(nt_f)
                if not (0 <= nt_i <= 100_000):
                    errores.append(_ef(fila_excel, "n_trades", "RANGE_INVALID",
                                       f"Valor {nt_i} fuera del rango permitido [0, 100000]."))
                    fila_ok = False
                else:
                    parsed["n_trades"] = nt_i
            except (ValueError, TypeError) as exc:
                errores.append(_ef(fila_excel, "n_trades", "TYPE_INVALID",
                                   f"Valor '{nt_raw}' no es un entero válido: {exc}"))
                fila_ok = False

        # ── hit_rate (Decimal opcional) ───────────────────────────────────────
        hr_raw = row.get("hit_rate")
        if _vacio(hr_raw):
            parsed["hit_rate"] = None
        else:
            try:
                hr_f = float(str(hr_raw).strip())
                if not (0.0 <= hr_f <= 1.0):
                    errores.append(_ef(fila_excel, "hit_rate", "RANGE_INVALID",
                                       f"Valor {hr_f:.6g} fuera del rango permitido [0, 1]."))
                    fila_ok = False
                else:
                    parsed["hit_rate"] = _to_decimal(hr_f)
            except (ValueError, TypeError) as exc:
                errores.append(_ef(fila_excel, "hit_rate", "TYPE_INVALID",
                                   f"Valor '{hr_raw}' no es un número válido: {exc}"))
                fila_ok = False

        # ── profit_factor (Decimal opcional) ─────────────────────────────────
        pf_raw = row.get("profit_factor")
        if _vacio(pf_raw):
            parsed["profit_factor"] = None
        else:
            try:
                pf_f = float(str(pf_raw).strip())
                if pf_f <= 0.0 or pf_f > 10.0:
                    errores.append(_ef(fila_excel, "profit_factor", "RANGE_INVALID",
                                       f"Valor {pf_f:.6g} fuera del rango permitido (0, 10]."))
                    fila_ok = False
                else:
                    parsed["profit_factor"] = _to_decimal(pf_f)
            except (ValueError, TypeError) as exc:
                errores.append(_ef(fila_excel, "profit_factor", "TYPE_INVALID",
                                   f"Valor '{pf_raw}' no es un número válido: {exc}"))
                fila_ok = False

        # ── WARN_CALMAR (warning, no bloquea) ─────────────────────────────────
        cagr_d = parsed.get("cagr")
        mdd_d = parsed.get("mdd")
        calmar_d = parsed.get("calmar")
        if cagr_d is not None and mdd_d is not None and calmar_d is not None:
            mdd_f = float(mdd_d)
            if abs(mdd_f) > 1e-9:
                calmar_exp = float(cagr_d) / abs(mdd_f)
                diff = abs(float(calmar_d) - calmar_exp)
                if diff >= 0.01:
                    errores.append(IngestaError(
                        archivo=_ARCHIVO,
                        fila=fila_excel,
                        columna="calmar",
                        codigo="WARN_CALMAR",
                        mensaje=(
                            f"Inconsistencia en calmar: valor={calmar_d}, "
                            f"esperado≈{calmar_exp:.4f} (cagr/|mdd|). "
                            f"Diferencia: {diff:.4f}."
                        ),
                        nivel="warning",
                    ))

        datos_parciales.append(parsed)
        fila_ok_flags.append(fila_ok)

        if "id_estrategia" in parsed:
            rows_by_strat[parsed["id_estrategia"]].append(
                (int(df_idx), parsed, fila_excel)
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Nivel 3: checks cruzados (post-loop)
    # ─────────────────────────────────────────────────────────────────────────

    for id_strat, group in rows_by_strat.items():

        # j) REF_NOT_FOUND ─────────────────────────────────────────────────────
        if id_strat not in strat_by_id:
            for df_idx, _parsed, fila_excel in group:
                errores.append(IngestaError(
                    archivo=_ARCHIVO,
                    fila=fila_excel,
                    columna="id_estrategia",
                    codigo="REF_NOT_FOUND",
                    mensaje=(
                        f"id_estrategia '{id_strat}' no existe en el catálogo "
                        "de estrategias validadas."
                    ),
                ))
                fila_ok_flags[df_idx] = False
            continue   # el resto requiere conocer la estrategia

        strat = strat_by_id[id_strat]
        tipo_strat: str = strat.get("tipo", "")
        fi_strat: date = strat["fecha_inicio"]
        ff_strat: date = strat["fecha_fin"]

        # k) ROW_COUNT_PER_STRATEGY ────────────────────────────────────────────
        periodos_validos = [
            p.get("periodo")
            for _, p, _ in group
            if p.get("periodo") in _PERIODO_VALS
        ]
        n_dev = periodos_validos.count("dev")
        n_oos = periodos_validos.count("oos")
        if n_dev != 1 or n_oos != 1:
            fila_primera = group[0][2]
            errores.append(IngestaError(
                archivo=_ARCHIVO,
                fila=fila_primera,
                columna="periodo",
                codigo="ROW_COUNT_PER_STRATEGY",
                mensaje=(
                    f"La estrategia '{id_strat}' debe tener exactamente 1 fila 'dev' "
                    f"y 1 fila 'oos'. Encontrado: {n_dev} dev, {n_oos} oos."
                ),
            ))
            for df_idx, _, _ in group:
                fila_ok_flags[df_idx] = False

        # Lookup rápido por periodo para los checks siguientes
        filas_por_periodo: dict[str, tuple[int, dict, int]] = {
            p.get("periodo"): (df_idx, p, fe)
            for df_idx, p, fe in group
            if p.get("periodo") in _PERIODO_VALS
        }

        for per, (df_idx, parsed, fila_excel) in filas_por_periodo.items():

            fi_p: Optional[date] = parsed.get("fecha_inicio_periodo")
            ff_p: Optional[date] = parsed.get("fecha_fin_periodo")

            # l) DATE_INVALID: fin >= inicio ───────────────────────────────────
            if fi_p is not None and ff_p is not None and ff_p < fi_p:
                errores.append(_ef(
                    fila_excel, "fecha_fin_periodo", "DATE_INVALID",
                    f"fecha_fin_periodo ({ff_p}) es anterior a "
                    f"fecha_inicio_periodo ({fi_p}).",
                ))
                fila_ok_flags[df_idx] = False

            # m) DATE_RANGE_OUT ────────────────────────────────────────────────
            if fi_p is not None and fi_p < fi_strat:
                errores.append(_ef(
                    fila_excel, "fecha_inicio_periodo", "DATE_RANGE_OUT",
                    f"fecha_inicio_periodo ({fi_p}) es anterior a la fecha_inicio "
                    f"de la estrategia '{id_strat}' ({fi_strat}).",
                ))
                fila_ok_flags[df_idx] = False

            if ff_p is not None and ff_p > ff_strat:
                errores.append(_ef(
                    fila_excel, "fecha_fin_periodo", "DATE_RANGE_OUT",
                    f"fecha_fin_periodo ({ff_p}) es posterior a la fecha_fin "
                    f"de la estrategia '{id_strat}' ({ff_strat}).",
                ))
                fila_ok_flags[df_idx] = False

            # o) NULL_CONDITIONAL (CONSTRAINT_CROSS) ──────────────────────────
            nt = parsed.get("n_trades")   # int | None
            hr = parsed.get("hit_rate")   # Decimal | None
            pf = parsed.get("profit_factor")  # Decimal | None

            if tipo_strat == "benchmark":
                for col_name, val in (
                    ("n_trades", nt), ("hit_rate", hr), ("profit_factor", pf)
                ):
                    if val is not None:
                        errores.append(_ef(
                            fila_excel, col_name, "CONSTRAINT_CROSS",
                            f"La estrategia '{id_strat}' es de tipo 'benchmark': "
                            f"'{col_name}' debe ser NULL pero tiene valor {val!r}.",
                        ))
                        fila_ok_flags[df_idx] = False

            elif tipo_strat == "estrategia_activa":
                for col_name, val in (
                    ("n_trades", nt), ("hit_rate", hr), ("profit_factor", pf)
                ):
                    if val is None:
                        errores.append(_ef(
                            fila_excel, col_name, "CONSTRAINT_CROSS",
                            f"La estrategia '{id_strat}' es de tipo 'estrategia_activa': "
                            f"'{col_name}' no puede ser NULL.",
                        ))
                        fila_ok_flags[df_idx] = False

        # n) DATE_OVERLAP: oos.inicio > dev.fin ───────────────────────────────
        if "dev" in filas_por_periodo and "oos" in filas_por_periodo:
            dev_df_idx, dev_parsed, _dev_fe = filas_por_periodo["dev"]
            oos_df_idx, oos_parsed, oos_fe = filas_por_periodo["oos"]
            dev_ff: Optional[date] = dev_parsed.get("fecha_fin_periodo")
            oos_fi: Optional[date] = oos_parsed.get("fecha_inicio_periodo")
            if dev_ff is not None and oos_fi is not None and oos_fi <= dev_ff:
                errores.append(IngestaError(
                    archivo=_ARCHIVO,
                    fila=oos_fe,
                    columna="fecha_inicio_periodo",
                    codigo="DATE_OVERLAP",
                    mensaje=(
                        f"Para la estrategia '{id_strat}': el periodo 'oos' empieza el "
                        f"{oos_fi}, que es igual o anterior al fin del 'dev' ({dev_ff}). "
                        "Los periodos no pueden solaparse."
                    ),
                ))
                fila_ok_flags[oos_df_idx] = False

    # ── Decisión final ────────────────────────────────────────────────────────
    errores_bloqueantes = [e for e in errores if e.nivel == "error"]
    if errores_bloqueantes:
        return [], errores

    datos_validos = [
        datos_parciales[i]
        for i, ok in enumerate(fila_ok_flags)
        if ok
    ]
    return datos_validos, errores


# ─────────────────────────────────────────────────────────────────────────────
# Helpers privados
# ─────────────────────────────────────────────────────────────────────────────

def _to_decimal(val: float) -> Decimal:
    """Convierte un float a Decimal con 4 decimales de precisión.

    Usa round() antes de str() para evitar artefactos de representación
    binaria (p.ej. 0.10000000000000001).
    """
    return Decimal(str(round(val, 4)))


def _e(
    codigo: str,
    mensaje: str,
    columna: Optional[str] = None,
    nivel: str = "error",
) -> IngestaError:
    """Error global (sin fila): estructura del archivo."""
    return IngestaError(
        archivo=_ARCHIVO,
        codigo=codigo,
        mensaje=mensaje,
        columna=columna,
        nivel=nivel,
    )


def _ef(fila: int, columna: str, codigo: str, mensaje: str) -> IngestaError:
    """Error de celda: fila + columna concretas."""
    return IngestaError(
        archivo=_ARCHIVO,
        fila=fila,
        columna=columna,
        codigo=codigo,
        mensaje=mensaje,
    )


def _vacio(val: object) -> bool:
    """True si el valor es NaN, None o cadena en blanco."""
    if val is None:
        return True
    try:
        if pd.isna(val):  # type: ignore[arg-type]
            return True
    except (TypeError, ValueError):
        pass
    return str(val).strip() == ""
