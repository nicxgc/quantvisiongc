"""Tests para app/services/ingesta/validador_metrics.py.

Convención de fixtures:
  - test_archivo_correcto usa los xlsx reales en C:/TFG/quantvisiongc/paquetes/export/.
    Si alguna ruta no existe el test se omite con pytest.skip.
  - El resto de tests generan xlsx temporales al vuelo con pandas + openpyxl
    en el directorio tmp_path que pytest limpia automáticamente.

Nota sobre WARN_ROW_COUNT:
  Los tests sintéticos (< 64 filas) siempre disparan WARN_ROW_COUNT.
  Las aserciones filtran por código específico para no verse afectadas.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from app.services.ingesta.validador_metrics import validar_metrics_summary
from app.services.ingesta.validador_strategies import validar_strategies

# ─────────────────────────────────────────────────────────────────────────────
# Rutas a archivos reales
# ─────────────────────────────────────────────────────────────────────────────

REAL_STRATEGIES = Path("C:/TFG/quantvisiongc/paquetes/export/strategies.xlsx")
REAL_METRICS    = Path("C:/TFG/quantvisiongc/paquetes/export/metrics_summary.xlsx")

# ─────────────────────────────────────────────────────────────────────────────
# Datos de referencia para tests sintéticos
# ─────────────────────────────────────────────────────────────────────────────

# Estrategia activa de referencia (como si viniera de validar_strategies)
_STRAT_ACTIVA: dict = {
    "id": "STRAT_1",
    "nombre": "Strategy Test 1",
    "tipo_activo": "accion",
    "tipo": "estrategia_activa",
    "categoria": "classifier",
    "descripcion": "Estrategia activa de prueba.",
    "fecha_inicio": date(2007, 1, 1),
    "fecha_fin": date(2026, 2, 19),
    "nivel_riesgo": 3,
}

# Benchmark de referencia
_STRAT_BENCH: dict = {
    "id": "BM_1",
    "nombre": "Benchmark Test 1",
    "tipo_activo": "etf_indice",
    "tipo": "benchmark",
    "categoria": "buy_and_hold",
    "descripcion": "Benchmark de prueba.",
    "fecha_inicio": date(2007, 1, 1),
    "fecha_fin": date(2026, 2, 19),
    "nivel_riesgo": 1,
}

# strategies_validas mínimo para tests sintéticos
_STRATS_VALIDAS = [_STRAT_ACTIVA, _STRAT_BENCH]

# ── Filas base completamente válidas (calmar = cagr / |mdd| exacto) ──────────

# STRAT_1 periodo dev
_DEV_ACTIVA: dict = {
    "id_estrategia":      "STRAT_1",
    "periodo":            "dev",
    "fecha_inicio_periodo": "2007-01-01",
    "fecha_fin_periodo":    "2025-04-10",
    "n_trades":           500,
    "cagr":               0.0500,
    "volatility":         0.1000,
    "sharpe":             0.8500,
    "sortino":            1.2300,
    "calmar":             0.5000,   # 0.05 / 0.10
    "mdd":               -0.1000,
    "hit_rate":           0.5200,
    "profit_factor":      1.1000,
}

# STRAT_1 periodo oos  (empieza el día siguiente al fin del dev)
_OOS_ACTIVA: dict = {
    "id_estrategia":      "STRAT_1",
    "periodo":            "oos",
    "fecha_inicio_periodo": "2025-04-11",
    "fecha_fin_periodo":    "2026-02-19",
    "n_trades":           45,
    "cagr":               0.0300,
    "volatility":         0.0900,
    "sharpe":             0.6000,
    "sortino":            0.9000,
    "calmar":             0.3000,   # 0.03 / 0.10
    "mdd":               -0.1000,
    "hit_rate":           0.5000,
    "profit_factor":      1.0500,
}

# BM_1 periodo dev
_DEV_BENCH: dict = {
    "id_estrategia":      "BM_1",
    "periodo":            "dev",
    "fecha_inicio_periodo": "2007-01-01",
    "fecha_fin_periodo":    "2025-04-10",
    "n_trades":           None,
    "cagr":               0.0600,
    "volatility":         0.1500,
    "sharpe":             0.7000,
    "sortino":            1.0000,
    "calmar":             0.4000,   # 0.06 / 0.15
    "mdd":               -0.1500,
    "hit_rate":           None,
    "profit_factor":      None,
}

# BM_1 periodo oos
_OOS_BENCH: dict = {
    "id_estrategia":      "BM_1",
    "periodo":            "oos",
    "fecha_inicio_periodo": "2025-04-11",
    "fecha_fin_periodo":    "2026-02-19",
    "n_trades":           None,
    "cagr":               0.0200,
    "volatility":         0.0800,
    "sharpe":             0.4000,
    "sortino":            0.6000,
    "calmar":             0.2000,   # 0.02 / 0.10
    "mdd":               -0.1000,
    "hit_rate":           None,
    "profit_factor":      None,
}


def _make_xlsx(tmp_path: Path, rows: list[dict]) -> Path:
    """Crea un xlsx temporal con las filas dadas. Devuelve la ruta del archivo."""
    df = pd.DataFrame(rows)
    ruta = tmp_path / "test_metrics.xlsx"
    df.to_excel(ruta, index=False)
    return ruta


def _bloqueantes(errores):
    return [e for e in errores if e.nivel == "error"]


def _advertencias(errores):
    return [e for e in errores if e.nivel == "warning"]


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: archivos reales → 64 dicts, 0 errores bloqueantes
# ─────────────────────────────────────────────────────────────────────────────

class TestArchivoReal:
    def test_archivo_correcto(self):
        if not REAL_STRATEGIES.exists() or not REAL_METRICS.exists():
            pytest.skip("Archivos reales no disponibles.")

        strats, s_errs = validar_strategies(REAL_STRATEGIES)
        assert strats, "validar_strategies devolvió lista vacía sobre el archivo real."

        datos, errores = validar_metrics_summary(REAL_METRICS, strats)

        bloq = _bloqueantes(errores)
        assert bloq == [], (
            "Errores bloqueantes inesperados:\n"
            + "\n".join(str(e) for e in bloq)
        )
        assert len(datos) == 64

        # Verificar tipos Python en el primer registro
        from decimal import Decimal as D
        d = datos[0]
        assert isinstance(d["id_estrategia"], str)
        assert isinstance(d["periodo"], str)
        assert d["periodo"] in {"dev", "oos"}
        assert isinstance(d["fecha_inicio_periodo"], date)
        assert isinstance(d["fecha_fin_periodo"], date)
        assert isinstance(d["cagr"], D)
        assert isinstance(d["mdd"], D)
        assert d["fecha_fin_periodo"] >= d["fecha_inicio_periodo"]


# ─────────────────────────────────────────────────────────────────────────────
# Tests de estructura (Nivel 1)
# ─────────────────────────────────────────────────────────────────────────────

class TestEstructura:
    def test_columna_faltante(self, tmp_path):
        """Archivo sin columna 'sharpe' → COL_MISSING bloqueante, datos vacíos."""
        filas = [{k: v for k, v in _DEV_ACTIVA.items() if k != "sharpe"}]
        ruta = _make_xlsx(tmp_path, filas)

        datos, errores = validar_metrics_summary(ruta, _STRATS_VALIDAS)

        assert datos == []
        missing = [e for e in errores if e.codigo == "COL_MISSING"]
        assert len(missing) == 1
        assert missing[0].columna == "sharpe"


# ─────────────────────────────────────────────────────────────────────────────
# Tests referenciales (Nivel 3j / k)
# ─────────────────────────────────────────────────────────────────────────────

class TestReferencial:
    def test_id_estrategia_inexistente(self, tmp_path):
        """Fila con id_estrategia='FAKE_X' no presente en strategies_validas → REF_NOT_FOUND."""
        fila = {**_DEV_ACTIVA, "id_estrategia": "FAKE_X"}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_metrics_summary(ruta, _STRATS_VALIDAS)

        assert datos == []
        ref_errs = [e for e in errores if e.codigo == "REF_NOT_FOUND"]
        assert len(ref_errs) == 1
        assert ref_errs[0].columna == "id_estrategia"
        assert "FAKE_X" in ref_errs[0].mensaje

    def test_estrategia_con_solo_un_periodo(self, tmp_path):
        """Solo fila 'dev' para STRAT_1 (falta 'oos') → ROW_COUNT_PER_STRATEGY."""
        ruta = _make_xlsx(tmp_path, [_DEV_ACTIVA])

        datos, errores = validar_metrics_summary(ruta, _STRATS_VALIDAS)

        assert datos == []
        rcp = [e for e in errores if e.codigo == "ROW_COUNT_PER_STRATEGY"]
        assert len(rcp) == 1
        assert "STRAT_1" in rcp[0].mensaje

    def test_estrategia_con_dos_filas_dev(self, tmp_path):
        """Dos filas 'dev' para STRAT_1, sin 'oos' → ROW_COUNT_PER_STRATEGY."""
        fila_dev2 = {**_DEV_ACTIVA, "cagr": 0.0100, "mdd": -0.0500, "calmar": 0.2000}
        ruta = _make_xlsx(tmp_path, [_DEV_ACTIVA, fila_dev2])

        datos, errores = validar_metrics_summary(ruta, _STRATS_VALIDAS)

        assert datos == []
        rcp = [e for e in errores if e.codigo == "ROW_COUNT_PER_STRATEGY"]
        assert len(rcp) == 1
        assert "2 dev" in rcp[0].mensaje


# ─────────────────────────────────────────────────────────────────────────────
# Tests de validación por celda (Nivel 2)
# ─────────────────────────────────────────────────────────────────────────────

class TestValidacionCelda:
    def test_periodo_invalido(self, tmp_path):
        """Fila con periodo='entrenamiento' → ENUM_INVALID en columna 'periodo'."""
        fila = {**_DEV_ACTIVA, "periodo": "entrenamiento"}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_metrics_summary(ruta, _STRATS_VALIDAS)

        assert datos == []
        enum_errs = [e for e in errores if e.codigo == "ENUM_INVALID"]
        assert len(enum_errs) == 1
        assert enum_errs[0].columna == "periodo"
        assert enum_errs[0].fila == 2

    def test_mdd_positivo(self, tmp_path):
        """Fila con mdd=0.05 (positivo) → RANGE_INVALID en columna 'mdd'."""
        fila = {**_DEV_ACTIVA, "mdd": 0.05}
        ruta = _make_xlsx(tmp_path, [fila])

        datos, errores = validar_metrics_summary(ruta, _STRATS_VALIDAS)

        assert datos == []
        range_errs = [e for e in errores if e.codigo == "RANGE_INVALID"]
        assert len(range_errs) == 1
        assert range_errs[0].columna == "mdd"
        assert range_errs[0].fila == 2


# ─────────────────────────────────────────────────────────────────────────────
# Tests de restricciones NULL condicionales (Nivel 3o)
# ─────────────────────────────────────────────────────────────────────────────

class TestNullCondicional:
    def test_benchmark_con_n_trades_no_nulo(self, tmp_path):
        """Benchmark con n_trades=100 → CONSTRAINT_CROSS en columna 'n_trades'."""
        # Fila dev: n_trades=100 (error)  |  fila oos: n_trades=None (correcto)
        dev_con_error = {**_DEV_BENCH, "n_trades": 100}
        ruta = _make_xlsx(tmp_path, [dev_con_error, _OOS_BENCH])

        datos, errores = validar_metrics_summary(ruta, _STRATS_VALIDAS)

        assert datos == []
        cc_errs = [e for e in errores if e.codigo == "CONSTRAINT_CROSS"]
        assert len(cc_errs) == 1
        assert cc_errs[0].columna == "n_trades"
        assert "benchmark" in cc_errs[0].mensaje

    def test_estrategia_activa_con_n_trades_nulo(self, tmp_path):
        """Estrategia activa con n_trades=None en fila dev → CONSTRAINT_CROSS."""
        # Solo n_trades nulo; hit_rate y profit_factor presentes para aislar el error
        dev_con_error = {**_DEV_ACTIVA, "n_trades": None}
        ruta = _make_xlsx(tmp_path, [dev_con_error, _OOS_ACTIVA])

        datos, errores = validar_metrics_summary(ruta, _STRATS_VALIDAS)

        assert datos == []
        cc_errs = [e for e in errores if e.codigo == "CONSTRAINT_CROSS"]
        assert len(cc_errs) == 1
        assert cc_errs[0].columna == "n_trades"
        assert "estrategia_activa" in cc_errs[0].mensaje


# ─────────────────────────────────────────────────────────────────────────────
# Tests de fechas cruzadas (Nivel 3l / m / n)
# ─────────────────────────────────────────────────────────────────────────────

class TestFechasCruzadas:
    def test_periodos_solapados(self, tmp_path):
        """oos.fecha_inicio <= dev.fecha_fin → DATE_OVERLAP.

        dev  : 2020-01-01 … 2025-06-30
        oos  : 2025-06-01 … 2026-02-19   ← empieza dentro del dev (solapamiento)
        """
        strat_amplia = {
            **_STRAT_ACTIVA,
            "fecha_inicio": date(2019, 1, 1),
            "fecha_fin":    date(2026, 12, 31),
        }

        dev = {
            **_DEV_ACTIVA,
            "fecha_inicio_periodo": "2020-01-01",
            "fecha_fin_periodo":    "2025-06-30",
        }
        oos = {
            **_OOS_ACTIVA,
            "fecha_inicio_periodo": "2025-06-01",   # ← antes del fin de dev
            "fecha_fin_periodo":    "2026-02-19",
        }
        ruta = _make_xlsx(tmp_path, [dev, oos])

        datos, errores = validar_metrics_summary(ruta, [strat_amplia, _STRAT_BENCH])

        assert datos == []
        ov_errs = [e for e in errores if e.codigo == "DATE_OVERLAP"]
        assert len(ov_errs) == 1
        assert ov_errs[0].columna == "fecha_inicio_periodo"
        assert "STRAT_1" in ov_errs[0].mensaje

    def test_periodo_fuera_rango_estrategia(self, tmp_path):
        """oos.fecha_fin posterior a strategies.fecha_fin → DATE_RANGE_OUT."""
        # La estrategia termina el 2026-02-19; el oos llega al 2026-12-31
        oos_extendido = {
            **_OOS_ACTIVA,
            "fecha_fin_periodo": "2026-12-31",   # ← excede fecha_fin de STRAT_1
        }
        ruta = _make_xlsx(tmp_path, [_DEV_ACTIVA, oos_extendido])

        datos, errores = validar_metrics_summary(ruta, _STRATS_VALIDAS)

        assert datos == []
        dr_errs = [e for e in errores if e.codigo == "DATE_RANGE_OUT"]
        assert len(dr_errs) == 1
        assert dr_errs[0].columna == "fecha_fin_periodo"
        assert "STRAT_1" in dr_errs[0].mensaje
