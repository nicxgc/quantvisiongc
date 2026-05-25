#!/usr/bin/env python
"""Seed CLI para QuantVisionGC.

Ingesta un paquete ZIP completo (strategies + metrics + equity_curves) en la
base de datos. Reutiliza la lógica de app.services.ingesta sin pasar por HTTP.

Ejemplos
--------
    python scripts/seed_paquete.py --zip C:/TFG/quantvisiongc/paquetes/paquete.zip
    python scripts/seed_paquete.py --zip ... --truncate
    python scripts/seed_paquete.py --zip ... --truncate --force
    python scripts/seed_paquete.py --zip ... --truncate --force --verbose

Códigos de salida
-----------------
    0  Éxito (o cancelación voluntaria de --truncate).
    1  Errores de validación en los xlsx.
    2  Conflicto de duplicados (BD ya poblada sin --truncate).
    3  Error inesperado.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# ── Ajuste de sys.path ────────────────────────────────────────────────────────
# El script vive en backend/scripts/; añadimos backend/ al path para que
# los imports "from app.*" funcionen igual que en los tests (misma estrategia
# que conftest.py).
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# ── Imports de la aplicación (después de ajustar sys.path) ───────────────────
from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.services.ingesta.ingesta_service import ingestar_paquete  # noqa: E402

# Número máximo de errores a mostrar en modo normal (--verbose muestra todos)
_MAX_ERRORES_MOSTRADOS = 10


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seed_paquete",
        description=(
            "Ingesta un paquete ZIP en la BD de QuantVisionGC "
            "sin pasar por la API HTTP."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--zip",
        required=True,
        metavar="PATH",
        help="Ruta al fichero ZIP con los tres xlsx del paquete.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help=(
            "Limpia la BD antes de ingerir (trunca estrategias, métricas, "
            "resultados, contrataciones y movimientos de monedero)."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Omite la confirmación interactiva de --truncate.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Muestra detalle adicional: primeros códigos insertados y todos los errores.",
    )
    return parser


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de salida
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_size(n_bytes: int) -> str:
    """Formatea bytes en KB/MB legible."""
    if n_bytes >= 1_048_576:
        return f"{n_bytes / 1_048_576:.1f} MB"
    return f"{n_bytes / 1024:.1f} KB"


def _print_errores(errores, verbose: bool) -> None:
    """Imprime la lista de errores con el nivel de detalle solicitado."""
    limite = len(errores) if verbose else _MAX_ERRORES_MOSTRADOS
    for err in errores[:limite]:
        partes = [f"  {err.archivo}"]
        if err.fila is not None:
            partes.append(f"fila {err.fila}")
        if err.columna is not None:
            partes.append(f"columna {err.columna}")
        partes.append(f"{err.codigo}")
        partes.append(err.mensaje)
        print(" — ".join(partes))
    if not verbose and len(errores) > _MAX_ERRORES_MOSTRADOS:
        resto = len(errores) - _MAX_ERRORES_MOSTRADOS
        print(f"  ... y {resto} error(es) más. Usa --verbose para verlos todos.")


# ─────────────────────────────────────────────────────────────────────────────
# Función principal
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # ── Leer el ZIP ───────────────────────────────────────────────────────────
    zip_path = Path(args.zip)
    if not zip_path.exists():
        print(f"ERROR: El archivo '{zip_path}' no existe.")
        sys.exit(3)

    zip_bytes = zip_path.read_bytes()
    print(f"\nLeyendo paquete: {zip_path} ({_fmt_size(len(zip_bytes))})")

    # ── Abrir sesión BD ───────────────────────────────────────────────────────
    db = SessionLocal()

    try:
        # ── --truncate ────────────────────────────────────────────────────────
        if args.truncate:
            if not args.force:
                print(
                    "\nATENCION: Esto borrará todas las estrategias, métricas, "
                    "resultados, contrataciones y movimientos de monedero."
                )
                print("El usuario admin se mantiene.")
                resp = input("¿Continuar? [s/N] ").strip()
                if resp.lower() != "s":
                    print("Operación cancelada.")
                    sys.exit(0)

            db.execute(
                text(
                    "TRUNCATE movimiento_monedero, contratacion, "
                    "resultado_estrategia, metrica_estrategia, estrategia "
                    "RESTART IDENTITY CASCADE"
                )
            )
            db.commit()
            print("Base de datos limpia. Procediendo con la ingesta...")

        # ── Ingesta ───────────────────────────────────────────────────────────
        print("Iniciando ingesta...")
        t0 = time.monotonic()
        summary, errores = ingestar_paquete(zip_bytes, db)
        elapsed = time.monotonic() - t0

        # ── Resultado ─────────────────────────────────────────────────────────
        if summary is not None:
            # Éxito
            warnings = [e for e in errores if e.nivel == "warning"]
            print(f"\nIngesta completada en {elapsed:.1f} segundos.\n")
            print(f"  Estrategias creadas:    {summary['estrategias_creadas']}")
            print(f"  Métricas creadas:       {summary['metricas_creadas']}")
            print(f"  Resultados creados:     {summary['resultados_creados']}")
            print(f"  Errores no bloqueantes: {len(warnings)}")

            if args.verbose and warnings:
                print("\nDetalle de advertencias:")
                _print_errores(warnings, verbose=True)
            elif warnings:
                first = warnings[0]
                print(
                    f"\n  Primer aviso: archivo={first.archivo} "
                    f"fila={first.fila} columna={first.columna} "
                    f"codigo={first.codigo} mensaje=\"{first.mensaje}\""
                )
            print()
            sys.exit(0)

        # Fallo: clasificar el tipo de error
        codigos = {e.codigo for e in errores}

        if "CONFLICT_DUPLICATE" in codigos:
            print("\nERROR: La base de datos ya contiene estrategias del paquete.")
            print("Usa --truncate para limpiar la BD antes de re-ingerir.\n")
            dup = next(e for e in errores if e.codigo == "CONFLICT_DUPLICATE")
            print(f"Detalle: {dup.mensaje}\n")
            sys.exit(2)

        if "DB_ERROR" in codigos:
            print("\nERROR: Fallo inesperado en la base de datos.\n")
            db_err = next(e for e in errores if e.codigo == "DB_ERROR")
            print(f"Detalle: {db_err.mensaje}\n")
            sys.exit(3)

        # Errores de validación (ZIP_INVALID, ZIP_INCOMPLETE, COL_MISSING, etc.)
        bloqueantes = [e for e in errores if e.nivel == "error"]
        print("\nERROR: La ingesta no se ejecutó por errores de validación.\n")
        print(f"Total de errores: {len(bloqueantes)}")
        _print_errores(bloqueantes, verbose=args.verbose)
        print()
        sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"\nERROR inesperado: {exc}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(3)
    finally:
        db.close()


if __name__ == "__main__":
    main()
