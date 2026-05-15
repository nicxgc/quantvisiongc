"""Seed para la tabla resultado_estrategia.

Genera 12 meses de series temporales diarias (días hábiles, lun-vie)
para las 3 primeras estrategias activas en BBDD, usando un proceso
GBM con perfiles agresivo, equilibrado y conservador.

Uso desde backend/:
    python -m scripts.seed_resultados
"""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from sqlalchemy import select, delete

from app.core.database import SessionLocal
from app.models.estrategia import Estrategia
from app.models.resultado_estrategia import ResultadoEstrategia


SEED = 42
INITIAL_EQUITY = 10_000.0
TRADING_DAYS_PER_YEAR = 252
SHARPE_WINDOW = 30
MONTHS_OF_HISTORY = 12

# (drift anual, volatilidad anual, etiqueta)
PROFILES = [
    (0.18, 0.25, "agresiva"),
    (0.10, 0.15, "equilibrada"),
    (0.05, 0.08, "conservadora"),
]


def business_days_back(end_date: date, months: int) -> list[date]:
    """Devuelve la lista de días hábiles (lun-vie) desde end_date hacia atrás
    cubriendo aproximadamente `months` meses, ordenada de más antigua a más reciente.
    """
    start_date = end_date - timedelta(days=months * 31)  # margen amplio
    days: list[date] = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # 0=lunes..4=viernes
            days.append(current)
        current += timedelta(days=1)
    return days


def generate_series(num_days: int, drift_annual: float, vol_annual: float, seed: int):
    """Devuelve cuatro arrays numpy: equity, retorno, drawdown, sharpe_ratio.

    - equity: serie de niveles partiendo de INITIAL_EQUITY.
    - retorno: retorno simple diario, primer día respecto a INITIAL_EQUITY.
    - drawdown: caída desde el máximo histórico (valor en [-1, 0]).
    - sharpe_ratio: Sharpe rolling anualizado sobre SHARPE_WINDOW días.
      Los primeros SHARPE_WINDOW - 1 días contienen np.nan.
    """
    rng = np.random.default_rng(seed)
    dt = 1.0 / TRADING_DAYS_PER_YEAR
    mu = (drift_annual - 0.5 * vol_annual ** 2) * dt
    sigma = vol_annual * np.sqrt(dt)

    log_returns = rng.normal(mu, sigma, num_days)
    equity = INITIAL_EQUITY * np.exp(np.cumsum(log_returns))

    prev = np.concatenate(([INITIAL_EQUITY], equity[:-1]))
    retorno = (equity - prev) / prev

    running_max = np.maximum.accumulate(equity)
    drawdown = (equity - running_max) / running_max

    sharpe = np.full(num_days, np.nan)
    for i in range(SHARPE_WINDOW - 1, num_days):
        window = retorno[i - SHARPE_WINDOW + 1 : i + 1]
        std = window.std(ddof=0)
        if std > 0:
            sharpe[i] = (window.mean() / std) * np.sqrt(TRADING_DAYS_PER_YEAR)

    return equity, retorno, drawdown, sharpe


def main() -> None:
    today = date.today()
    fechas = business_days_back(today, MONTHS_OF_HISTORY)
    num_days = len(fechas)
    print(f"Generando {num_days} días hábiles hasta {today.isoformat()}.")

    with SessionLocal() as session:
        # Carga las primeras 3 estrategias activas por id ascendente.
        stmt = (
            select(Estrategia)
            .where(Estrategia.activa.is_(True))
            .order_by(Estrategia.id.asc())
            .limit(len(PROFILES))
        )
        estrategias = list(session.scalars(stmt))

        if not estrategias:
            print("ERROR: no hay estrategias activas en BBDD. Crea al menos una antes de ejecutar el seed.")
            return

        print(f"Estrategias detectadas: {[(e.id, e.nombre) for e in estrategias]}")

        for idx, estrategia in enumerate(estrategias):
            drift, vol, etiqueta = PROFILES[idx]
            print(f"  -> Estrategia id={estrategia.id} ({etiqueta}): drift={drift}, vol={vol}")

            # Limpieza idempotente
            session.execute(
                delete(ResultadoEstrategia).where(
                    ResultadoEstrategia.id_estrategia == estrategia.id
                )
            )

            equity, retorno, drawdown, sharpe = generate_series(
                num_days=num_days,
                drift_annual=drift,
                vol_annual=vol,
                seed=SEED + idx,  # semilla distinta por estrategia
            )

            filas = []
            for i, fecha in enumerate(fechas):
                sharpe_val = None if np.isnan(sharpe[i]) else Decimal(f"{sharpe[i]:.4f}")
                filas.append(
                    ResultadoEstrategia(
                        id_estrategia=estrategia.id,
                        fecha=fecha,
                        equity=Decimal(f"{equity[i]:.6f}"),
                        retorno=Decimal(f"{retorno[i]:.6f}"),
                        drawdown=Decimal(f"{drawdown[i]:.6f}"),
                        sharpe_ratio=sharpe_val,
                    )
                )

            session.add_all(filas)
            print(f"     Insertadas {len(filas)} filas.")

        session.commit()
        print("Seed completado correctamente.")


if __name__ == "__main__":
    main()
