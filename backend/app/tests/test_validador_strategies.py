"""Tests para app/services/ingesta/validador_strategies.py.

Convención de fixtures:
  - test_archivo_correcto usa el xlsx real en C:/TFG/quantvisiongc/paquetes/export/.
    Si la ruta no existe, el test se omite con pytest.skip.
  - El resto de tests generan xlsx temporales al vuelo con pandas + openpyxl
    en el directorio tmp_path que pytest limpia automáticamente.
    No se comiten binarios al repositorio.

Nota sobre WARN_ROW_COUNT:
  Los tests con 1–4 filas siempre disparan la advertencia WARN_ROW_COUNT (≠ 32).
  Esto es correcto y esperado; las aserciones filtran por nivel='error' o por
  código específico para no verse afectadas por esa advertencia.
"""

from pathlib import Path

import pandas as pd
import pytest

from app.services.ingesta.validador_strategies import validar_strategies

# ─────────────────────────────────────────────────────────────────────────────
# Datos de referencia
# ─────────────────────────────────────────────────────────────────────────────

REAL_XLSX = Path("C:/TFG/quantvisiongc/paquetes/export/strategies.xlsx")

# Fila base completamente válida para construir casos de prueba.
BASE_ROW: dict = {
    "id": "TEST_STRAT_1",
    "nombre": "Strategy Test 1",
    "tipo_activo": "accion",
    "tipo": "estrategia_activa",
    "categoria": "classifier",
    "descripcion": "Descripcion de prueba suficientemente larga para ser válida.",
    "fecha_inicio": "2020-01-01",
    "fecha_fin": "2024-12-31",
    "nivel_riesgo": 3,
}


def _make_xlsx(tmp_path: Path, rows: list[dict], extra_cols: dict | None = None) -> Path:
    """Crea un xlsx temporal con las filas dadas. Devuelve la ruta del archivo."""
    df = pd.DataFrame(rows)
    if extra_cols:
        for col, val in extra_cols.items():
            df[col] = val
    ruta = tmp_path / "test_strategies.xlsx"
    df.to_excel(ruta, index=False)
    return ruta


def _bloqueantes(errores):
    return [e for e in errores if e.nivel == "error"]


def _advertencias(errores):
    return [e for e in errores if e.nivel == "warning"]


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: archivo real de 32 filas → 0 errores, 32 dicts
# ─────────────────────────────────────────────────────────────────────────────

class TestArchivoReal:
    def test_archivo_correcto(self):
        if not REAL_XLSX.exists():
            pytest.skip(f"Archivo real no disponible: {REAL_XLSX}")

        datos, errores = validar_strategies(REAL_XLSX)

        bloq = _bloqueantes(errores)
        assert bloq == [], f"Errores bloqueantes inesperados:\n" + "\n".join(str(e) for e in bloq)
        assert len(datos) == 32

        # Verificar tipos Python en el primer registro
        d = datos[0]
        from datetime import date
        assert isinstance(d["id"], str)
        assert isinstance(d["nombre"], str)
        assert isinstance(d["fecha_inicio"], date)
        assert isinstance(d["fecha_fin"], date)
        assert isinstance(d["nivel_riesgo"], int)
        assert d["fecha_fin"] >= d["fecha_inicio"]


# ─────────────────────────────────────────────────────────────────────────────
# Tests de estructura (Nivel 1)
# ─────────────────────────────────────────────────────────────────────────────

class TestEstructura:
    def test_columna_faltante(self, tmp_path):
        """Archivo sin columna 'tipo' → COL_MISSING bloqueante, datos vacíos."""
        fila = {k: v for k, v in BASE_ROW.items() if k != "tipo"}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_strategies(ruta)

        assert datos == []
        missing = [e for e in errores if e.codigo == "COL_MISSING"]
        assert len(missing) == 1
        assert missing[0].columna == "tipo"

    def test_columna_extra_no_bloquea(self, tmp_path):
        """Columna adicional → advertencia COL_UNEXPECTED, datos se devuelven igualmente."""
        ruta = _make_xlsx(tmp_path, [BASE_ROW], extra_cols={"columna_inventada": "valor"})

        datos, errores = validar_strategies(ruta)

        assert _bloqueantes(errores) == []
        advertencias = _advertencias(errores)
        assert any(e.codigo == "COL_UNEXPECTED" and e.columna == "columna_inventada"
                   for e in advertencias)
        assert len(datos) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Tests de validación por celda (Nivel 2)
# ─────────────────────────────────────────────────────────────────────────────

class TestValidacionCelda:
    def test_enum_invalido_tipo(self, tmp_path):
        """tipo con valor fuera de catálogo → ENUM_INVALID en columna 'tipo'."""
        fila = {**BASE_ROW, "tipo": "tipo_inexistente"}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_strategies(ruta)

        assert datos == []
        enum_errs = [e for e in errores if e.codigo == "ENUM_INVALID"]
        assert len(enum_errs) == 1
        assert enum_errs[0].columna == "tipo"
        assert enum_errs[0].fila == 2

    def test_nivel_riesgo_fuera_rango(self, tmp_path):
        """nivel_riesgo=10 → RANGE_INVALID."""
        fila = {**BASE_ROW, "nivel_riesgo": 10}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_strategies(ruta)

        assert datos == []
        range_errs = [e for e in errores if e.codigo == "RANGE_INVALID"]
        assert len(range_errs) == 1
        assert range_errs[0].columna == "nivel_riesgo"
        assert range_errs[0].fila == 2


# ─────────────────────────────────────────────────────────────────────────────
# Tests cruzados (Nivel 3)
# ─────────────────────────────────────────────────────────────────────────────

class TestValidacionCruzada:
    def test_id_duplicado(self, tmp_path):
        """Dos filas con mismo id → dos errores ID_DUPLICATED (uno por fila)."""
        fila1 = {**BASE_ROW, "id": "ID_DUPLICADO"}
        fila2 = {**BASE_ROW, "id": "ID_DUPLICADO", "nombre": "Strategy Test 2"}
        ruta = _make_xlsx(tmp_path, [fila1, fila2])

        datos, errores = validar_strategies(ruta)

        assert datos == []
        dup_errs = [e for e in errores if e.codigo == "ID_DUPLICATED"]
        assert len(dup_errs) == 2
        filas_reportadas = {e.fila for e in dup_errs}
        assert filas_reportadas == {2, 3}   # fila 2 y fila 3 de Excel

    def test_fecha_invertida(self, tmp_path):
        """fecha_fin < fecha_inicio → DATE_INVALID con mención a 'anterior'."""
        fila = {**BASE_ROW, "fecha_inicio": "2024-12-31", "fecha_fin": "2020-01-01"}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_strategies(ruta)

        assert datos == []
        date_errs = [e for e in errores if e.codigo == "DATE_INVALID"]
        assert len(date_errs) == 1
        assert "anterior" in date_errs[0].mensaje
        assert date_errs[0].columna == "fecha_fin"
        assert date_errs[0].fila == 2

    def test_cross_constraint_benchmark_no_es_buy_and_hold(self, tmp_path):
        """tipo='benchmark' con categoria='classifier' → CONSTRAINT_CROSS."""
        fila = {**BASE_ROW, "tipo": "benchmark", "categoria": "classifier"}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_strategies(ruta)

        assert datos == []
        cc_errs = [e for e in errores if e.codigo == "CONSTRAINT_CROSS"]
        assert len(cc_errs) == 1
        assert "benchmark" in cc_errs[0].mensaje
        assert cc_errs[0].fila == 2


# ─────────────────────────────────────────────────────────────────────────────
# Test de no-aborto ante múltiples errores (Nivel 2 y 3 combinados)
# ─────────────────────────────────────────────────────────────────────────────

class TestAcumulacionErrores:
    def test_multiples_errores_no_aborta(self, tmp_path):
        """Archivo con 3 tipos distintos de errores en filas distintas.

        El validador NO debe abortar al primer fallo: debe devolver los 3
        errores acumulados para que el admin los corrija de una pasada.

        Errores introducidos:
          - Fila 2 (fila_enum):  tipo='invalido'  → ENUM_INVALID
          - Fila 3 (fila_range): nivel_riesgo=0   → RANGE_INVALID
          - Fila 4 (fila_fecha): fecha_fin < fecha_inicio → DATE_INVALID
        """
        fila_enum = {**BASE_ROW, "id": "TEST_2", "nombre": "Test 2",
                     "tipo": "invalido"}
        fila_range = {**BASE_ROW, "id": "TEST_3", "nombre": "Test 3",
                      "nivel_riesgo": 0}
        fila_fecha = {**BASE_ROW, "id": "TEST_4", "nombre": "Test 4",
                      "fecha_inicio": "2025-01-01", "fecha_fin": "2020-01-01"}

        ruta = _make_xlsx(tmp_path, [fila_enum, fila_range, fila_fecha])
        datos, errores = validar_strategies(ruta)

        assert datos == []

        bloq = _bloqueantes(errores)
        codigos = {e.codigo for e in bloq}
        assert "ENUM_INVALID" in codigos, f"Falta ENUM_INVALID en {codigos}"
        assert "RANGE_INVALID" in codigos, f"Falta RANGE_INVALID en {codigos}"
        assert "DATE_INVALID" in codigos, f"Falta DATE_INVALID en {codigos}"

        # Exactamente 3 errores bloqueantes (uno por fila)
        assert len(bloq) == 3, (
            f"Se esperaban 3 errores bloqueantes, se obtuvieron {len(bloq)}:\n"
            + "\n".join(str(e) for e in bloq)
        )
