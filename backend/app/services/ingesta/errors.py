"""Tipos de error para el módulo de ingesta de datos."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IngestaError:
    """Representa un único problema detectado durante la validación de un archivo de ingesta.

    Campos
    ------
    archivo : str
        Nombre del archivo analizado (p.ej. "strategies.xlsx").
    codigo : str
        Código corto que identifica el tipo de error. Valores posibles:
          FILE_MISSING      — el archivo no existe en la ruta indicada.
          FILE_INVALID      — el archivo no puede leerse como xlsx.
          FILE_EMPTY        — el archivo no contiene filas de datos.
          COL_MISSING       — falta una columna requerida.
          COL_UNEXPECTED    — columna extra no esperada (nivel='warning').
          WARN_ROW_COUNT    — número de filas distinto del esperado (nivel='warning').
          TYPE_INVALID      — celda nula o tipo/longitud incorrectos.
          DATE_INVALID      — fecha no parseable o fecha_fin < fecha_inicio.
          ENUM_INVALID      — valor no está en el catálogo permitido.
          RANGE_INVALID     — valor numérico fuera del rango permitido.
          ID_DUPLICATED     — el campo 'id' aparece más de una vez en el archivo.
          CONSTRAINT_CROSS  — inconsistencia entre dos columnas de la misma fila.
    mensaje : str
        Descripción legible para el administrador que revise el archivo.
    fila : int | None
        Número de fila en Excel (1-indexed, cabecera = fila 1, primer dato = fila 2).
        None si el error es a nivel global (p.ej. columna faltante, archivo vacío).
    columna : str | None
        Nombre de la columna afectada. None para errores a nivel de fila completa
        o para restricciones cruzadas que involucran varias columnas.
    nivel : str
        'error'   — impide que se devuelvan datos; la ingesta no puede continuar.
        'warning' — informativo; los datos válidos se devuelven igualmente.
    """

    archivo: str
    codigo: str
    mensaje: str
    fila: Optional[int] = None
    columna: Optional[str] = None
    nivel: str = "error"

    def __str__(self) -> str:
        partes = [f"[{self.nivel.upper()}][{self.codigo}]"]
        if self.fila is not None:
            partes.append(f"fila {self.fila}")
        if self.columna is not None:
            partes.append(f"col '{self.columna}'")
        partes.append(self.mensaje)
        return " — ".join(partes)
