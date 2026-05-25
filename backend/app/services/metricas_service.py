"""Servicio de métricas y series temporales.

Lógica de negocio para:
- Recuperar la serie temporal de una estrategia (filtrable por periodo dev/oos).
- Calcular los KPIs agregados del dashboard de un usuario.
- Recuperar el feed de actividad reciente del usuario.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import literal, select, union_all
from sqlalchemy.orm import Session

from app.models.contratacion import Contratacion, EstadoContratacion
from app.models.enums import PeriodoEnum
from app.models.estrategia import Estrategia
from app.models.resultado_estrategia import ResultadoEstrategia
from app.models.usuario import Usuario
from app.schemas.dashboard import AccionReciente, DashboardKPIs


def obtener_actividad_reciente(
    db: Session,
    id_usuario: int,
    limite: int,
) -> list[AccionReciente]:
    """Devuelve los últimos `limite` eventos de actividad del usuario (RF-27).

    Usa UNION ALL entre dos SELECT sobre contratacion para tratar cada
    evento (contratacion / cancelacion) como una fila independiente en el
    feed, ordenados cronológicamente de más reciente a más antiguo.
    Devuelve [] si el usuario no tiene actividad.
    """
    # Evento "contratacion": una fila por cada contratación creada.
    select_contrataciones = (
        select(
            literal("contratacion").label("tipo"),
            Contratacion.fecha_contratacion.label("fecha"),
            Estrategia.nombre.label("nombre_estrategia"),
            Estrategia.precio_subscripcion.label("monto"),
        )
        .join(Estrategia, Estrategia.id == Contratacion.id_estrategia)
        .where(Contratacion.id_usuario == id_usuario)
    )

    # Evento "cancelacion": solo las contrataciones que tienen fecha_cancelacion.
    select_cancelaciones = (
        select(
            literal("cancelacion").label("tipo"),
            Contratacion.fecha_cancelacion.label("fecha"),
            Estrategia.nombre.label("nombre_estrategia"),
            Estrategia.precio_subscripcion.label("monto"),
        )
        .join(Estrategia, Estrategia.id == Contratacion.id_estrategia)
        .where(Contratacion.id_usuario == id_usuario)
        .where(Contratacion.fecha_cancelacion.is_not(None))
    )

    # UNION ALL → subquery → ordenar por fecha descendente → limitar.
    unioned = union_all(select_contrataciones, select_cancelaciones).subquery()
    stmt = select(unioned).order_by(unioned.c.fecha.desc()).limit(limite)

    rows = db.execute(stmt).all()
    return [
        AccionReciente(
            tipo=row.tipo,
            fecha=row.fecha,
            nombre_estrategia=row.nombre_estrategia,
            monto=row.monto,
        )
        for row in rows
    ]


def obtener_serie_estrategia(
    db: Session,
    id_estrategia: int,
    periodo: Optional[str] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
) -> Optional[list[ResultadoEstrategia]]:
    """Devuelve la serie temporal de una estrategia ordenada por fecha asc.

    - `periodo`: 'dev', 'oos', o None para ambos. Por defecto None (todos los periodos).
    - Devuelve None si la estrategia no existe (para que el router responda 404).
    - Devuelve una lista (posiblemente vacía) si la estrategia existe.
    """
    if db.get(Estrategia, id_estrategia) is None:
        return None

    stmt = (
        select(ResultadoEstrategia)
        .where(ResultadoEstrategia.id_estrategia == id_estrategia)
        .order_by(ResultadoEstrategia.periodo, ResultadoEstrategia.fecha.asc())
    )
    if periodo is not None:
        stmt = stmt.where(ResultadoEstrategia.periodo == periodo)
    if desde is not None:
        stmt = stmt.where(ResultadoEstrategia.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(ResultadoEstrategia.fecha <= hasta)

    return list(db.scalars(stmt))


def obtener_kpis_dashboard(db: Session, usuario_id: int) -> DashboardKPIs:
    """Calcula los KPIs agregados del dashboard del usuario.

    Para cada contratación activa del usuario:
      - Toma el equity de la estrategia (periodo OOS) en su fecha de contratación
        (o el primer dato posterior si la contratación cae en festivo).
      - Toma el equity OOS más reciente disponible para esa estrategia.
      - Escala monto_invertido por (equity_final / equity_inicial) para
        obtener el valor actual de esa contratación.

    Usa exclusivamente el periodo OOS como referencia de valoración porque
    representa el rendimiento real fuera de la muestra de entrenamiento.

    Si el usuario no tiene contrataciones activas, todos los agregados
    monetarios son 0.
    """
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise ValueError(f"Usuario {usuario_id} no encontrado.")

    contrataciones = list(
        db.scalars(
            select(Contratacion)
            .where(Contratacion.id_usuario == usuario_id)
            .where(Contratacion.estado == EstadoContratacion.ACTIVA)
        )
    )

    total_invertido = Decimal("0")
    valor_actual = Decimal("0")

    for c in contrataciones:
        # Primer equity OOS disponible en o después de la fecha de contratación.
        equity_inicial = db.scalar(
            select(ResultadoEstrategia.equity)
            .where(ResultadoEstrategia.id_estrategia == c.id_estrategia)
            .where(ResultadoEstrategia.periodo == PeriodoEnum.OOS)
            .where(ResultadoEstrategia.fecha >= c.fecha_contratacion)
            .order_by(ResultadoEstrategia.fecha.asc())
            .limit(1)
        )
        # Equity OOS más reciente de la estrategia.
        equity_final = db.scalar(
            select(ResultadoEstrategia.equity)
            .where(ResultadoEstrategia.id_estrategia == c.id_estrategia)
            .where(ResultadoEstrategia.periodo == PeriodoEnum.OOS)
            .order_by(ResultadoEstrategia.fecha.desc())
            .limit(1)
        )

        total_invertido += c.monto_invertido

        if equity_inicial is None or equity_final is None or equity_inicial == 0:
            # Sin datos OOS todavía o serie vacía: valoramos al coste.
            valor_actual += c.monto_invertido
        else:
            factor = equity_final / equity_inicial
            valor_actual += c.monto_invertido * factor

    pnl_absoluto = valor_actual - total_invertido
    rentabilidad_total = (
        pnl_absoluto / total_invertido if total_invertido > 0 else Decimal("0")
    )

    return DashboardKPIs(
        saldo_monedero=usuario.saldo_monedero,
        total_invertido=total_invertido,
        valor_actual=valor_actual,
        pnl_absoluto=pnl_absoluto,
        rentabilidad_total=rentabilidad_total,
        num_estrategias_activas=len(contrataciones),
    )
