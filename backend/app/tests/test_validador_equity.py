"""Tests para app/services/ingesta/validador_equity.py.

Convención de fixtures:
  - test_archivo_real usa los xlsx reales en C:/TFG/quantvisiongc/paquetes/export/.
    Si alguna ruta no existe el test se omite con pytest.skip.
  - El resto de tests generan xlsx pequeños al vuelo con pandas + openpyxl
    en el directorio tmp_path que pytest limpia automáticamente.

test_performance:
  Usa unittest.mock.patch para sustituir pd.read_excel por un DataFrame
  sintético de 50 000 filas generado en memoria.  Esto mide la lógica de
  validación pura (sin I/O xlsx), que es el cuello de botella bajo nuestro
  control.  El lector xlsx de pandas para 50 k filas tarda ≈10 s en esta
  máquina (openpyxl limit) — ese tiempo está fuera del alcance de este código.
"""

import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from app.services.ingesta.validador_equity import validar_equity_curves
from app.services.ingesta.validador_strategies import validar_strategies
from app.services.ingesta.validador_metrics import validar_metrics_summary

# ─────────────────────────────────────────────────────────────────────────────
# Rutas a archivos reales
# ─────────────────────────────────────────────────────────────────────────────

REAL_DIR = Path("C:/TFG/quantvisiongc/paquetes/export")
REAL_STRATEGIES = REAL_DIR / "strategies.xlsx"
REAL_METRICS    = REAL_DIR / "metrics_summary.xlsx"
REAL_EQUITY     = REAL_DIR / "equity_curves.xlsx"

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures de referencia para tests sintéticos
# ─────────────────────────────────────────────────────────────────────────────

_STRAT_1: dict = {
    "id": "STRAT_1",
    "nombre": "Estrategia Test 1",
    "tipo_activo": "accion",
    "tipo": "estrategia_activa",
    "categoria": "classifier",
    "descripcion": "Test.",
    "fecha_inicio": date(2020, 1, 1),
    "fecha_fin": date(2026, 12, 31),
    "nivel_riesgo": 3,
}

_STRATS_VALIDAS: list[dict] = [_STRAT_1]

# Métricas para STRAT_1 / dev  (fecha_fin_periodo = 2025-12-31)
_METRIC_DEV: dict = {
    "id_estrategia":      "STRAT_1",
    "periodo":            "dev",
    "fecha_inicio_periodo": date(2020, 1, 1),
    "fecha_fin_periodo":    date(2025, 12, 31),
}

# Métricas para STRAT_1 / oos
_METRIC_OOS: dict = {
    "id_estrategia":      "STRAT_1",
    "periodo":            "oos",
    "fecha_inicio_periodo": date(2026, 1, 1),
    "fecha_fin_periodo":    date(2026, 12, 31),
}

_METRICS_VALIDAS: list[dict] = [_METRIC_DEV, _METRIC_OOS]

# Fila base completamente válida
BASE_ROW: dict = {
    "id_estrategia": "STRAT_1",
    "periodo":       "dev",
    "fecha":         date(2020, 1, 2),
    "equity":        100_000.0,
    "drawdown":      0.0,
    "retorno":       0.0,
}


def _make_xlsx(tmp_path: Path, rows: list[dict]) -> Path:
    """Crea un xlsx temporal con las filas dadas."""
    df = pd.DataFrame(rows)
    ruta = tmp_path / "test_equity.xlsx"
    df.to_excel(ruta, index=False)
    return ruta


def _bloqueantes(errores):
    return [e for e in errores if e.nivel == "error"]


def _advertencias(errores):
    return [e for e in errores if e.nivel == "warning"]


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: archivo real → ≈136 942 dicts, 0 errores bloqueantes
# ─────────────────────────────────────────────────────────────────────────────

class TestArchivoReal:
    def test_archivo_real(self):
        if not REAL_STRATEGIES.exists() or not REAL_METRICS.exists() or not REAL_EQUITY.exists():
            pytest.skip("Archivos reales no disponibles.")

        strats, _ = validar_strategies(REAL_STRATEGIES)
        metrics, _ = validar_metrics_summary(REAL_METRICS, strats)
        datos, errores = validar_equity_curves(REAL_EQUITY, strats, metrics)

        bloq = _bloqueantes(errores)
        assert bloq == [], (
            "Errores bloqueantes inesperados:\n" + "\n".join(str(e) for e in bloq)
        )
        # El paquete real tiene 136 942 filas
        assert len(datos) > 100_000

        # Verificar tipos Python en el primer registro
        d = datos[0]
        assert isinstance(d["id_estrategia"], str)
        assert isinstance(d["periodo"], str)
        assert isinstance(d["fecha"], date)
        assert isinstance(d["equity"], Decimal)
        assert isinstance(d["drawdown"], Decimal)
        assert isinstance(d["retorno"], Decimal)


# ─────────────────────────────────────────────────────────────────────────────
# Tests de estructura (Nivel 1)
# ─────────────────────────────────────────────────────────────────────────────

class TestEstructura:
    def test_columna_faltante(self, tmp_path):
        """Archivo sin columna 'drawdown' → COL_MISSING bloqueante, datos vacíos."""
        fila = {k: v for k, v in BASE_ROW.items() if k != "drawdown"}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_equity_curves(ruta, _STRATS_VALIDAS, _METRICS_VALIDAS)

        assert datos == []
        missing = [e for e in errores if e.codigo == "COL_MISSING"]
        assert len(missing) == 1
        assert missing[0].columna == "drawdown"


# ─────────────────────────────────────────────────────────────────────────────
# Tests de validación por celda (Nivel 2)
# ─────────────────────────────────────────────────────────────────────────────

class TestValidacionCelda:
    def test_equity_negativo(self, tmp_path):
        """equity=-100 → RANGE_INVALID en columna 'equity'."""
        fila = {**BASE_ROW, "equity": -100.0}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_equity_curves(ruta, _STRATS_VALIDAS, _METRICS_VALIDAS)

        assert datos == []
        range_errs = [e for e in errores if e.codigo == "RANGE_INVALID"]
        assert len(range_errs) == 1
        assert range_errs[0].columna == "equity"
        assert range_errs[0].fila == 2

    def test_drawdown_positivo(self, tmp_path):
        """drawdown=0.05 (positivo) → RANGE_INVALID en columna 'drawdown'."""
        fila = {**BASE_ROW, "drawdown": 0.05}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_equity_curves(ruta, _STRATS_VALIDAS, _METRICS_VALIDAS)

        assert datos == []
        range_errs = [e for e in errores if e.codigo == "RANGE_INVALID"]
        assert len(range_errs) == 1
        assert range_errs[0].columna == "drawdown"
        assert range_errs[0].fila == 2

    def test_periodo_invalido(self, tmp_path):
        """periodo='train' → ENUM_INVALID en columna 'periodo'."""
        fila = {**BASE_ROW, "periodo": "train"}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_equity_curves(ruta, _STRATS_VALIDAS, _METRICS_VALIDAS)

        assert datos == []
        enum_errs = [e for e in errores if e.codigo == "ENUM_INVALID"]
        assert len(enum_errs) == 1
        assert enum_errs[0].columna == "periodo"
        assert enum_errs[0].fila == 2


# ─────────────────────────────────────────────────────────────────────────────
# Tests de checks cross-row (Nivel 3)
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossRow:
    def test_par_id_periodo_inexistente(self, tmp_path):
        """Par (STRAT_1, oos) no está en _METRICS_VALIDAS (solo hay dev) → REF_NOT_FOUND."""
        # _METRICS_VALIDAS contiene (STRAT_1, dev) y (STRAT_1, oos) → uso solo dev
        metrics_solo_dev = [_METRIC_DEV]  # sin _METRIC_OOS
        fila = {**BASE_ROW, "periodo": "oos"}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_equity_curves(ruta, _STRATS_VALIDAS, metrics_solo_dev)

        assert datos == []
        ref_errs = [e for e in errores if e.codigo == "REF_NOT_FOUND"]
        assert len(ref_errs) == 1
        assert "oos" in ref_errs[0].mensaje

    def test_fecha_duplicada(self, tmp_path):
        """Dos filas con misma (id_estrategia, periodo, fecha) → DATE_UNIQUE."""
        fila1 = {**BASE_ROW}
        fila2 = {**BASE_ROW, "equity": 101_000.0}  # misma fecha, equity diferente
        ruta = _make_xlsx(tmp_path, [fila1, fila2])

        datos, errores = validar_equity_curves(ruta, _STRATS_VALIDAS, _METRICS_VALIDAS)

        assert datos == []
        dup_errs = [e for e in errores if e.codigo == "DATE_UNIQUE"]
        assert len(dup_errs) == 2   # ambas filas son reportadas
        assert all(e.columna == "fecha" for e in dup_errs)

    def test_fecha_fuera_de_rango(self, tmp_path):
        """fecha=2030-01-01 posterior a fecha_fin_periodo=2025-12-31 → DATE_RANGE_OUT."""
        fila = {**BASE_ROW, "fecha": date(2030, 1, 1)}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_equity_curves(ruta, _STRATS_VALIDAS, _METRICS_VALIDAS)

        assert datos == []
        dr_errs = [e for e in errores if e.codigo == "DATE_RANGE_OUT"]
        assert len(dr_errs) == 1
        assert dr_errs[0].columna == "fecha"
        assert dr_errs[0].fila == 2

    def test_fechas_desordenadas_reordena(self, tmp_path):
        """Filas desordenadas por fecha → WARN_DATE_REORDERED (no bloqueante)
        y datos devueltos en orden cronológico correcto."""
        # Fila inicial válida (equity=100k, drawdown=0, retorno=0) - la segunda en xlsx
        fila_ini = {**BASE_ROW, "fecha": date(2020, 1, 2),
                    "equity": 100_000.0, "drawdown": 0.0, "retorno": 0.0}
        # Segunda fila válida (equity sube 1%) - la primera en xlsx (¡orden invertido!)
        fila_sig = {**BASE_ROW, "fecha": date(2020, 1, 7),
                    "equity": 101_000.0, "drawdown": 0.0, "retorno": 0.01}
        # Escribimos fila_sig ANTES que fila_ini → desordenado
        ruta = _make_xlsx(tmp_path, [fila_sig, fila_ini])

        datos, errores = validar_equity_curves(ruta, _STRATS_VALIDAS, _METRICS_VALIDAS)

        # El warning no bloquea; datos se devuelven
        assert len(datos) == 2
        warns = [e for e in errores if e.codigo == "WARN_DATE_REORDERED"]
        assert len(warns) == 1
        # Datos en orden cronológico correcto
        assert datos[0]["fecha"] == date(2020, 1, 2)
        assert datos[1]["fecha"] == date(2020, 1, 7)
        bloq = _bloqueantes(errores)
        assert bloq == []


# ─────────────────────────────────────────────────────────────────────────────
# Tests de coherencia matemática (Nivel 4 — warnings no bloqueantes)
# ─────────────────────────────────────────────────────────────────────────────

class TestCoherenciaMatematica:
    def test_drawdown_incoherente_es_warn(self, tmp_path):
        """drawdown manipulado a valor incorrecto → WARN_DRAWDOWN, datos igualmente devueltos."""
        fila_ini = {**BASE_ROW}                            # equity=100k, dd=0, ret=0
        # equity baja a 90k; drawdown correcto sería -0.1 pero ponemos -0.5
        fila_bad = {**BASE_ROW, "fecha": date(2020, 1, 7),
                    "equity": 90_000.0, "drawdown": -0.5, "retorno": -0.1}
        ruta = _make_xlsx(tmp_path, [fila_ini, fila_bad])

        datos, errores = validar_equity_curves(ruta, _STRATS_VALIDAS, _METRICS_VALIDAS)

        # El warning NO bloquea
        assert len(datos) == 2
        bloq = _bloqueantes(errores)
        assert bloq == []
        dd_warns = [e for e in errores if e.codigo == "WARN_DRAWDOWN"]
        assert len(dd_warns) == 1
        assert dd_warns[0].columna == "drawdown"

    def test_retorno_incoherente_es_warn(self, tmp_path):
        """retorno manipulado a valor incorrecto → WARN_RETURN, datos igualmente devueltos."""
        fila_ini = {**BASE_ROW}                            # equity=100k, dd=0, ret=0
        # equity baja a 90k; retorno correcto sería -0.1 pero ponemos -0.5
        fila_bad = {**BASE_ROW, "fecha": date(2020, 1, 7),
                    "equity": 90_000.0, "drawdown": -0.1, "retorno": -0.5}
        ruta = _make_xlsx(tmp_path, [fila_ini, fila_bad])

        datos, errores = validar_equity_curves(ruta, _STRATS_VALIDAS, _METRICS_VALIDAS)

        # El warning NO bloquea
        assert len(datos) == 2
        bloq = _bloqueantes(errores)
        assert bloq == []
        ret_warns = [e for e in errores if e.codigo == "WARN_RETURN"]
        assert len(ret_warns) == 1
        assert ret_warns[0].columna == "retorno"


# ─────────────────────────────────────────────────────────────────────────────
# Test de performance
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformance:
    def test_performance(self, tmp_path):
        """La lógica de validación (sin I/O xlsx) procesa 50 000 filas en < 3 s.

        Se usa unittest.mock.patch para sustituir pd.read_excel por un
        DataFrame sintético generado en memoria, midiendo exclusivamente
        la lógica del validador y no el tiempo de carga del fichero xlsx
        (que es un límite de openpyxl, fuera del alcance de este código).
        """
        N = 50_000

        strat_perf = {
            "id": "PERF_1",
            "nombre": "Perf Test",
            "tipo_activo": "accion",
            "tipo": "estrategia_activa",
            "categoria": "classifier",
            "descripcion": "Perf.",
            "fecha_inicio": date(2020, 1, 1),
            "fecha_fin": date(2299, 12, 31),
            "nivel_riesgo": 3,
        }
        metrics_perf = [
            {
                "id_estrategia": "PERF_1",
                "periodo": "dev",
                "fecha_inicio_periodo": date(2020, 1, 1),
                "fecha_fin_periodo": date(2299, 12, 31),
            }
        ]

        # Generar serie de equity matemáticamente consistente
        np.random.seed(42)
        ret = np.random.normal(0.0002, 0.005, N)
        ret[0] = 0.0
        equity = 100_000.0 * np.cumprod(1 + ret)
        cummax_eq = np.maximum.accumulate(equity)
        drawdown = equity / cummax_eq - 1

        dates = pd.date_range("2020-01-01", periods=N, freq="B")
        df_big = pd.DataFrame({
            "id_estrategia": ["PERF_1"] * N,
            "periodo":       ["dev"] * N,
            "fecha":         dates,
            "equity":        equity,
            "drawdown":      drawdown,
            "retorno":       ret,
        })

        # Un archivo vacío que solo sirve para pasar el check ruta.exists()
        dummy = tmp_path / "perf_dummy.xlsx"
        dummy.touch()

        with patch(
            "app.services.ingesta.validador_equity.pd.read_excel",
            return_value=df_big,
        ):
            t0 = time.perf_counter()
            datos, errs = validar_equity_curves(dummy, [strat_perf], metrics_perf)
            t1 = time.perf_counter()

        elapsed = t1 - t0
        assert elapsed < 3.0, (
            f"La lógica de validación tardó {elapsed:.2f}s para {N} filas "
            f"(límite: 3.0 s). Revisar operaciones no-vectorizadas."
        )
        assert len(datos) == N, f"Se esperaban {N} dicts, se obtuvieron {len(datos)}"
        bloq = [e for e in errs if e.nivel == "error"]
        assert bloq == [], f"Errores bloqueantes inesperados: {bloq}"
