"""Tests de integración para el endpoint POST /api/v1/admin/ingesta/paquete.

Organización
------------
TestAutorizacion       (2)  — 401 y 403 sin tocar BD
TestValidacionArchivo  (5)  — extensión, zip corrupto, zip incompleto,
                               errores xlsx, estructura de respuesta
TestIngestaReal        (2)  — usa archivos reales; omitido si no están
                               disponibles en C:/TFG/quantvisiongc/paquetes/export/

Total: 9 tests

Notas
-----
- Se usa TestClient (sync) para que FastAPI use las dependencias reales.
- Los tokens se generan directamente con create_access_token (sin password).
  user_id=7 → admin@test.com (rol ADMIN)
  user_id=1 → nico@test.com  (rol USER)
- Los tests que insertan datos hacen TRUNCATE TABLE estrategia CASCADE al
  finalizar para no contaminar la BD entre ejecuciones.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.main import app

# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────

ENDPOINT = "/api/v1/admin/ingesta/paquete"

REAL_STRATEGIES = Path("C:/TFG/quantvisiongc/paquetes/export/strategies.xlsx")
REAL_METRICS    = Path("C:/TFG/quantvisiongc/paquetes/export/metrics_summary.xlsx")
REAL_EQUITY     = Path("C:/TFG/quantvisiongc/paquetes/export/equity_curves.xlsx")

_REAL_FILES_AVAILABLE = (
    REAL_STRATEGIES.exists()
    and REAL_METRICS.exists()
    and REAL_EQUITY.exists()
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures de módulo
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    token = create_access_token(subject=7)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers() -> dict[str, str]:
    token = create_access_token(subject=1)
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_zip_bytes(files: dict[str, bytes]) -> bytes:
    """Crea un ZIP en memoria con los ficheros dados. Devuelve los bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _xlsx_bytes(df: pd.DataFrame) -> bytes:
    """Serializa un DataFrame a bytes xlsx (openpyxl)."""
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def _real_zip_bytes() -> bytes:
    """Crea un ZIP en memoria con los tres xlsx reales."""
    return _make_zip_bytes(
        {
            "strategies.xlsx":     REAL_STRATEGIES.read_bytes(),
            "metrics_summary.xlsx": REAL_METRICS.read_bytes(),
            "equity_curves.xlsx":  REAL_EQUITY.read_bytes(),
        }
    )


def _truncate_db() -> None:
    """Elimina todos los datos de estrategia (y sus cascadas) de la BD."""
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE estrategia CASCADE"))
        db.commit()
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TestAutorizacion — 2 tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAutorizacion:
    def test_sin_token_returns_401(self, client: TestClient) -> None:
        """Petición sin header Authorization → 401 Unauthorized."""
        r = client.post(
            ENDPOINT,
            files={"archivo": ("paquete.zip", b"data", "application/zip")},
        )
        assert r.status_code == 401

    def test_usuario_normal_returns_403(
        self, client: TestClient, user_headers: dict
    ) -> None:
        """JWT con rol=user (no admin) → 403 Forbidden."""
        r = client.post(
            ENDPOINT,
            headers=user_headers,
            files={"archivo": ("paquete.zip", b"data", "application/zip")},
        )
        assert r.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# TestValidacionArchivo — 5 tests
# ─────────────────────────────────────────────────────────────────────────────

class TestValidacionArchivo:
    def test_extension_invalida_returns_400(
        self, client: TestClient, admin_headers: dict
    ) -> None:
        """Subir un archivo .pdf (no .zip) → 400 con código ZIP_INVALID."""
        r = client.post(
            ENDPOINT,
            headers=admin_headers,
            files={"archivo": ("paquete.pdf", b"data", "application/pdf")},
        )
        assert r.status_code == 400
        body = r.json()
        assert body["status"] == "error"
        codigos = {e["codigo"] for e in body["errores"]}
        assert "ZIP_INVALID" in codigos

    def test_zip_corrupto_returns_400(
        self, client: TestClient, admin_headers: dict
    ) -> None:
        """Bytes aleatorios con extensión .zip → 400 con código ZIP_INVALID."""
        r = client.post(
            ENDPOINT,
            headers=admin_headers,
            files={
                "archivo": (
                    "paquete.zip",
                    b"ESTO NO ES UN ZIP VALIDO!!!",
                    "application/zip",
                )
            },
        )
        assert r.status_code == 400
        body = r.json()
        assert body["status"] == "error"
        codigos = {e["codigo"] for e in body["errores"]}
        assert "ZIP_INVALID" in codigos

    def test_zip_incompleto_returns_400(
        self, client: TestClient, admin_headers: dict
    ) -> None:
        """ZIP con solo strategies.xlsx (faltan los otros dos) → 400 ZIP_INCOMPLETE."""
        df = pd.DataFrame([{"id": "S1"}])
        zip_bytes = _make_zip_bytes({"strategies.xlsx": _xlsx_bytes(df)})
        r = client.post(
            ENDPOINT,
            headers=admin_headers,
            files={"archivo": ("paquete.zip", zip_bytes, "application/zip")},
        )
        assert r.status_code == 400
        body = r.json()
        assert body["status"] == "error"
        codigos = {e["codigo"] for e in body["errores"]}
        assert "ZIP_INCOMPLETE" in codigos

    def test_zip_con_errores_validacion_returns_400(
        self, client: TestClient, admin_headers: dict
    ) -> None:
        """ZIP con strategies.xlsx sin columna 'id' → 400 con errores de validación."""
        # strategies.xlsx sin la columna 'id' → COL_MISSING bloqueante
        df_s = pd.DataFrame([{"nombre": "S1", "tipo": "estrategia_activa"}])
        df_m = pd.DataFrame([{"id_estrategia": "S1", "periodo": "dev"}])
        df_e = pd.DataFrame([{"id_estrategia": "S1", "periodo": "dev"}])
        zip_bytes = _make_zip_bytes(
            {
                "strategies.xlsx":      _xlsx_bytes(df_s),
                "metrics_summary.xlsx": _xlsx_bytes(df_m),
                "equity_curves.xlsx":   _xlsx_bytes(df_e),
            }
        )
        r = client.post(
            ENDPOINT,
            headers=admin_headers,
            files={"archivo": ("paquete.zip", zip_bytes, "application/zip")},
        )
        assert r.status_code == 400
        body = r.json()
        assert body["status"] == "error"
        assert len(body["errores"]) > 0
        assert body["summary"] is None

    def test_respuesta_error_tiene_campos_requeridos(
        self, client: TestClient, admin_headers: dict
    ) -> None:
        """Una respuesta de error contiene exactamente status, summary y errores."""
        r = client.post(
            ENDPOINT,
            headers=admin_headers,
            files={
                "archivo": ("paquete.zip", b"NO_ES_ZIP", "application/zip")
            },
        )
        body = r.json()
        assert "status" in body
        assert "errores" in body
        assert "summary" in body
        # En un error, summary siempre es null
        assert body["summary"] is None
        # Cada error tiene los campos del schema
        for err in body["errores"]:
            assert "codigo" in err
            assert "mensaje" in err
            assert "archivo" in err
            assert "nivel" in err


# ─────────────────────────────────────────────────────────────────────────────
# TestIngestaReal — 2 tests (omitidos si no hay archivos reales)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not _REAL_FILES_AVAILABLE,
    reason="Archivos reales no disponibles en C:/TFG/quantvisiongc/paquetes/export/",
)
class TestIngestaReal:
    """Tests que insertan datos reales en BD.  Se ejecutan solo si los xlsx
    están disponibles.  Cada test limpia la BD al finalizar con TRUNCATE."""

    @pytest.fixture(autouse=True)
    def cleanup_after(self):
        """Teardown: elimina los datos insertados por cada test."""
        yield
        _truncate_db()

    def test_ingesta_real_ok_returns_200(
        self, client: TestClient, admin_headers: dict
    ) -> None:
        """Paquete real → 200 con summary correcto (32 estrategias, 64 métricas)."""
        r = client.post(
            ENDPOINT,
            headers=admin_headers,
            files={
                "archivo": (
                    "paquete.zip",
                    _real_zip_bytes(),
                    "application/zip",
                )
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "ok"
        assert body["summary"] is not None
        assert body["summary"]["estrategias_creadas"] == 32
        assert body["summary"]["metricas_creadas"] == 64
        assert body["summary"]["resultados_creados"] > 100_000

    def test_ingesta_duplicada_returns_409(
        self, client: TestClient, admin_headers: dict
    ) -> None:
        """Re-ingestar el mismo paquete → 409 CONFLICT_DUPLICATE."""
        zip_bytes = _real_zip_bytes()

        # Primera ingesta debe ser exitosa
        r1 = client.post(
            ENDPOINT,
            headers=admin_headers,
            files={"archivo": ("paquete.zip", zip_bytes, "application/zip")},
        )
        assert r1.status_code == 200, f"Primera ingesta falló: {r1.text}"

        # Segunda ingesta con los mismos datos → 409
        r2 = client.post(
            ENDPOINT,
            headers=admin_headers,
            files={"archivo": ("paquete.zip", zip_bytes, "application/zip")},
        )
        assert r2.status_code == 409, r2.text
        body = r2.json()
        assert body["status"] == "error"
        codigos = {e["codigo"] for e in body["errores"]}
        assert "CONFLICT_DUPLICATE" in codigos
