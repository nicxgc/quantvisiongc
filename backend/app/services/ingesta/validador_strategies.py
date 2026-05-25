"""Validador estricto para el archivo strategies.xlsx del paquete de ingesta.

Realiza la validación en tres niveles antes de devolver datos listos para BD:

  Nivel 1 — Estructural (aborta si falla):
    a) El archivo existe y es un xlsx válido.
    b) Tiene al menos 1 fila de datos.
    c) Tiene exactamente las 9 columnas requeridas (COL_MISSING es bloqueante;
       COL_UNEXPECTED es un aviso no bloqueante).
    d) Tiene 32 filas (WARN_ROW_COUNT, no bloqueante).

  Nivel 2 — Por celda (recorre TODAS las filas, acumula errores):
    e) Campos obligatorios no nulos ni vacíos (TYPE_INVALID).
    f) Longitudes de strings dentro de los límites.
    g) Valores enum en el catálogo permitido (ENUM_INVALID).
    h) nivel_riesgo en [1, 7] (RANGE_INVALID).
    i) Fechas parseables como ISO YYYY-MM-DD (DATE_INVALID).

  Nivel 3 — Cruzadas (cross-row / cross-column):
    j) id único en el archivo (ID_DUPLICATED, uno por fila implicada).
    k) fecha_fin >= fecha_inicio (DATE_INVALID).
    l) Consistencia tipo ↔ categoria (CONSTRAINT_CROSS):
       - tipo='benchmark'        → categoria DEBE ser 'buy_and_hold'
       - tipo='estrategia_activa' → categoria NO PUEDE ser 'buy_and_hold'

CONVENCIÓN DE INDEXACIÓN DE FILAS
----------------------------------
Las filas se reportan 1-indexed contando la cabecera como fila 1.
La primera fila de datos es la fila 2, que coincide con la fila 2 en Excel.
Así el administrador puede abrir el xlsx y localizar el error directamente.

CONTRATO DE RETORNO
-------------------
    datos, errores = validar_strategies(ruta)

  - Si hay errores bloqueantes (nivel='error'):  datos = [],   errores = [...]
  - Solo advertencias (nivel='warning'):         datos = [...], errores = [advertencias]
  - Sin ningún problema:                         datos = [...], errores = []

  Cada dict en `datos` contiene:
    id (str), nombre (str), tipo_activo (str), tipo (str), categoria (str),
    descripcion (str), fecha_inicio (date), fecha_fin (date), nivel_riesgo (int)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from app.services.ingesta.errors import IngestaError

# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────

_ARCHIVO = "strategies.xlsx"
_FILAS_ESPERADAS = 32

_COLUMNAS_ESPERADAS: list[str] = [
    "id", "nombre", "tipo_activo", "tipo", "categoria",
    "descripcion", "fecha_inicio", "fecha_fin", "nivel_riesgo",
]

_TIPO_ACTIVO_VALS: frozenset[str] = frozenset(
    {"accion", "etf_indice", "etf_materia_prima", "divisa"}
)
_TIPO_VALS: frozenset[str] = frozenset({"estrategia_activa", "benchmark"})
_CATEGORIA_VALS: frozenset[str] = frozenset(
    {"classifier", "classifier_volscaling", "arima_garch", "buy_and_hold"}
)


# ─────────────────────────────────────────────────────────────────────────────
# Función pública
# ─────────────────────────────────────────────────────────────────────────────

def validar_strategies(ruta_xlsx: Path) -> tuple[list[dict], list[IngestaError]]:
    """Valida strategies.xlsx y devuelve los datos parseados o la lista de errores.

    Ver docstring de módulo para el contrato completo y la convención de filas.
    """
    errores: list[IngestaError] = []

    # ── Nivel 1a: El archivo existe ───────────────────────────────────────────
    if not ruta_xlsx.exists():
        errores.append(_e(
            codigo="FILE_MISSING",
            mensaje=f"Archivo no encontrado: {ruta_xlsx}",
        ))
        return [], errores

    # ── Nivel 1a: Archivo legible como xlsx ───────────────────────────────────
    try:
        df = pd.read_excel(ruta_xlsx, dtype=str, keep_default_na=True)
    except Exception as exc:
        errores.append(_e(
            codigo="FILE_INVALID",
            mensaje=f"No se pudo leer el archivo como xlsx: {exc}",
        ))
        return [], errores

    # ── Nivel 1b: Al menos 1 fila de datos ───────────────────────────────────
    if len(df) == 0:
        errores.append(_e(
            codigo="FILE_EMPTY",
            mensaje="El archivo no contiene filas de datos.",
        ))
        return [], errores

    # ── Nivel 1c: Columnas requeridas presentes ───────────────────────────────
    cols_presentes = set(df.columns)
    cols_esperadas = set(_COLUMNAS_ESPERADAS)

    for col in sorted(cols_esperadas - cols_presentes):
        errores.append(_e(
            codigo="COL_MISSING",
            columna=col,
            mensaje=f"Columna requerida '{col}' no encontrada en el archivo.",
        ))

    for col in sorted(cols_presentes - cols_esperadas):
        errores.append(_e(
            codigo="COL_UNEXPECTED",
            columna=col,
            mensaje=f"Columna inesperada '{col}' presente en el archivo. Se ignorará.",
            nivel="warning",
        ))

    # Si falta alguna columna requerida no podemos continuar
    if any(e.codigo == "COL_MISSING" for e in errores):
        return [], errores

    # ── Nivel 1d: Conteo de filas (no bloqueante) ─────────────────────────────
    if len(df) != _FILAS_ESPERADAS:
        errores.append(_e(
            codigo="WARN_ROW_COUNT",
            mensaje=(
                f"Se esperaban {_FILAS_ESPERADAS} filas de datos, "
                f"se encontraron {len(df)}. Verificar que el archivo está completo."
            ),
            nivel="warning",
        ))

    # ── Niveles 2 y 3 (por fila): acumula errores sin abortar ─────────────────
    ids_vistos: dict[str, list[tuple[int, int]]] = {}   # id → [(fila_excel, df_index)]
    datos_parciales: list[dict] = []
    fila_ok_flags: list[bool] = []

    for df_idx, row in df.iterrows():
        fila_excel = int(df_idx) + 2   # cabecera=1 → datos desde fila 2
        fila_ok = True
        parsed: dict = {}

        # ── id ────────────────────────────────────────────────────────────────
        id_raw = row.get("id")
        if _vacio(id_raw):
            errores.append(_ef(fila_excel, "id", "TYPE_INVALID",
                               "El campo 'id' no puede estar vacío."))
            fila_ok = False
        else:
            id_str = str(id_raw).strip()
            if len(id_str) > 50:
                errores.append(_ef(fila_excel, "id", "TYPE_INVALID",
                                   f"'id' excede 50 caracteres (longitud: {len(id_str)})."))
                fila_ok = False
            else:
                parsed["id"] = id_str
                ids_vistos.setdefault(id_str, []).append((fila_excel, int(df_idx)))

        # ── nombre ────────────────────────────────────────────────────────────
        nombre_raw = row.get("nombre")
        if _vacio(nombre_raw):
            errores.append(_ef(fila_excel, "nombre", "TYPE_INVALID",
                               "El campo 'nombre' no puede estar vacío."))
            fila_ok = False
        else:
            nombre_str = str(nombre_raw).strip()
            if len(nombre_str) > 100:
                errores.append(_ef(fila_excel, "nombre", "TYPE_INVALID",
                                   f"'nombre' excede 100 caracteres (longitud: {len(nombre_str)})."))
                fila_ok = False
            else:
                parsed["nombre"] = nombre_str

        # ── tipo_activo ───────────────────────────────────────────────────────
        ta_raw = row.get("tipo_activo")
        if _vacio(ta_raw):
            errores.append(_ef(fila_excel, "tipo_activo", "TYPE_INVALID",
                               "El campo 'tipo_activo' no puede estar vacío."))
            fila_ok = False
        else:
            ta_str = str(ta_raw).strip()
            if ta_str not in _TIPO_ACTIVO_VALS:
                errores.append(_ef(fila_excel, "tipo_activo", "ENUM_INVALID",
                                   f"Valor '{ta_str}' no permitido. "
                                   f"Valores válidos: {sorted(_TIPO_ACTIVO_VALS)}."))
                fila_ok = False
            else:
                parsed["tipo_activo"] = ta_str

        # ── tipo ──────────────────────────────────────────────────────────────
        tipo_raw = row.get("tipo")
        if _vacio(tipo_raw):
            errores.append(_ef(fila_excel, "tipo", "TYPE_INVALID",
                               "El campo 'tipo' no puede estar vacío."))
            fila_ok = False
        else:
            tipo_str = str(tipo_raw).strip()
            if tipo_str not in _TIPO_VALS:
                errores.append(_ef(fila_excel, "tipo", "ENUM_INVALID",
                                   f"Valor '{tipo_str}' no permitido. "
                                   f"Valores válidos: {sorted(_TIPO_VALS)}."))
                fila_ok = False
            else:
                parsed["tipo"] = tipo_str

        # ── categoria ─────────────────────────────────────────────────────────
        cat_raw = row.get("categoria")
        if _vacio(cat_raw):
            errores.append(_ef(fila_excel, "categoria", "TYPE_INVALID",
                               "El campo 'categoria' no puede estar vacío."))
            fila_ok = False
        else:
            cat_str = str(cat_raw).strip()
            if cat_str not in _CATEGORIA_VALS:
                errores.append(_ef(fila_excel, "categoria", "ENUM_INVALID",
                                   f"Valor '{cat_str}' no permitido. "
                                   f"Valores válidos: {sorted(_CATEGORIA_VALS)}."))
                fila_ok = False
            else:
                parsed["categoria"] = cat_str

        # ── descripcion ───────────────────────────────────────────────────────
        desc_raw = row.get("descripcion")
        if _vacio(desc_raw):
            errores.append(_ef(fila_excel, "descripcion", "TYPE_INVALID",
                               "El campo 'descripcion' no puede estar vacío."))
            fila_ok = False
        else:
            parsed["descripcion"] = str(desc_raw).strip()

        # ── fecha_inicio ──────────────────────────────────────────────────────
        fi_raw = row.get("fecha_inicio")
        fecha_inicio: Optional[date] = None
        if _vacio(fi_raw):
            errores.append(_ef(fila_excel, "fecha_inicio", "TYPE_INVALID",
                               "El campo 'fecha_inicio' no puede estar vacío."))
            fila_ok = False
        else:
            try:
                fecha_inicio = date.fromisoformat(str(fi_raw).strip())
                parsed["fecha_inicio"] = fecha_inicio
            except ValueError:
                errores.append(_ef(fila_excel, "fecha_inicio", "DATE_INVALID",
                                   f"Formato de fecha inválido '{fi_raw}'. Se espera YYYY-MM-DD."))
                fila_ok = False

        # ── fecha_fin ─────────────────────────────────────────────────────────
        ff_raw = row.get("fecha_fin")
        fecha_fin: Optional[date] = None
        if _vacio(ff_raw):
            errores.append(_ef(fila_excel, "fecha_fin", "TYPE_INVALID",
                               "El campo 'fecha_fin' no puede estar vacío."))
            fila_ok = False
        else:
            try:
                fecha_fin = date.fromisoformat(str(ff_raw).strip())
                parsed["fecha_fin"] = fecha_fin
            except ValueError:
                errores.append(_ef(fila_excel, "fecha_fin", "DATE_INVALID",
                                   f"Formato de fecha inválido '{ff_raw}'. Se espera YYYY-MM-DD."))
                fila_ok = False

        # ── nivel_riesgo ──────────────────────────────────────────────────────
        nr_raw = row.get("nivel_riesgo")
        if _vacio(nr_raw):
            errores.append(_ef(fila_excel, "nivel_riesgo", "TYPE_INVALID",
                               "El campo 'nivel_riesgo' no puede estar vacío."))
            fila_ok = False
        else:
            try:
                nr_str = str(nr_raw).strip()
                nr_float = float(nr_str)
                if nr_float != int(nr_float):
                    raise ValueError("El valor tiene parte decimal, se esperaba entero.")
                nr_int = int(nr_float)
                if not (1 <= nr_int <= 7):
                    errores.append(_ef(fila_excel, "nivel_riesgo", "RANGE_INVALID",
                                       f"Valor {nr_int} fuera del rango permitido [1, 7]."))
                    fila_ok = False
                else:
                    parsed["nivel_riesgo"] = nr_int
            except (ValueError, TypeError) as exc:
                errores.append(_ef(fila_excel, "nivel_riesgo", "TYPE_INVALID",
                                   f"Valor '{nr_raw}' no es un entero válido: {exc}"))
                fila_ok = False

        # ── Nivel 3 cross-column (mismo fila) ────────────────────────────────

        # fecha_fin >= fecha_inicio
        if fecha_inicio is not None and fecha_fin is not None:
            if fecha_fin < fecha_inicio:
                errores.append(_ef(fila_excel, "fecha_fin", "DATE_INVALID",
                                   f"fecha_fin ({fecha_fin}) es anterior a "
                                   f"fecha_inicio ({fecha_inicio})."))
                fila_ok = False

        # tipo ↔ categoria
        tipo_p = parsed.get("tipo")
        cat_p = parsed.get("categoria")
        if tipo_p is not None and cat_p is not None:
            if tipo_p == "benchmark" and cat_p != "buy_and_hold":
                errores.append(_efr(fila_excel, "CONSTRAINT_CROSS",
                                    f"tipo='benchmark' requiere categoria='buy_and_hold' "
                                    f"(encontrado: '{cat_p}')."))
                fila_ok = False
            elif tipo_p == "estrategia_activa" and cat_p == "buy_and_hold":
                errores.append(_efr(fila_excel, "CONSTRAINT_CROSS",
                                    "tipo='estrategia_activa' no puede tener "
                                    "categoria='buy_and_hold'."))
                fila_ok = False

        datos_parciales.append(parsed)
        fila_ok_flags.append(fila_ok)

    # ── Nivel 3 cross-row: unicidad de id ─────────────────────────────────────
    for id_str, entries in ids_vistos.items():
        if len(entries) > 1:
            filas_implicadas = [e[0] for e in entries]
            for fila_excel, df_idx in entries:
                errores.append(IngestaError(
                    archivo=_ARCHIVO,
                    fila=fila_excel,
                    columna="id",
                    codigo="ID_DUPLICATED",
                    mensaje=(
                        f"El id '{id_str}' está duplicado. "
                        f"Aparece en las filas Excel: {filas_implicadas}."
                    ),
                ))
                fila_ok_flags[df_idx] = False

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
# Helpers privados de construcción de errores
# ─────────────────────────────────────────────────────────────────────────────

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


def _efr(fila: int, codigo: str, mensaje: str) -> IngestaError:
    """Error de fila sin columna concreta (cross-column constraint)."""
    return IngestaError(
        archivo=_ARCHIVO,
        fila=fila,
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
