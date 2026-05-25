"""Lógica de negocio para operaciones CRUD sobre la entidad Estrategia."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.contratacion import Contratacion, EstadoContratacion
from app.models.enums import PeriodoEnum, TipoEstrategia
from app.models.estrategia import Estrategia, EstadoEstrategia
from app.models.metrica_estrategia import MetricaEstrategia
from app.models.resultado_estrategia import ResultadoEstrategia
from app.schemas.estrategia import (
    EstrategiaAdminRead,
    EstrategiaCatalogRead,
    EstrategiaCreate,
    EstrategiaDetalleRead,
    EstrategiaRead,
    EstrategiaUpdate,
)
from app.schemas.metrica_estrategia import MetricaEstrategiaRead
from app.services.contratacion_service import cancelar_contrataciones_de_estrategia


def crear_estrategia(db: Session, datos: EstrategiaCreate) -> Estrategia:
    """Crea una nueva estrategia tras verificar unicidad de nombre y codigo_estrategia.

    Lanza ValueError si ya existe una estrategia con el mismo nombre o código.
    """
    if db.scalar(select(Estrategia).where(Estrategia.nombre == datos.nombre)) is not None:
        raise ValueError(f"Ya existe una estrategia con el nombre '{datos.nombre}'.")
    if db.scalar(select(Estrategia).where(Estrategia.codigo_estrategia == datos.codigo_estrategia)) is not None:
        raise ValueError(f"Ya existe una estrategia con el código '{datos.codigo_estrategia}'.")

    estrategia = Estrategia(**datos.model_dump())
    db.add(estrategia)
    db.commit()
    db.refresh(estrategia)
    return estrategia


def listar_estrategias(
    db: Session,
    solo_activas: bool = True,
    incluir_benchmarks: bool = False,
) -> list[EstrategiaCatalogRead]:
    """Catálogo público de estrategias con métricas OOS resumidas.

    Aplica LEFT JOIN con metrica_estrategia (periodo='oos') para adjuntar los
    cuatro indicadores clave. El LEFT JOIN garantiza que estrategias sin datos
    OOS cargados aún aparezcan en el catálogo (con campos *_oos en None).

    Parámetros:
      - solo_activas: si True (por defecto) filtra activa=True y estado='activa'.
      - incluir_benchmarks: si False (por defecto) excluye las de tipo 'benchmark'.
        Cuando True devuelve también los benchmarks (útil para el comparador).
    """
    # Subquery: una fila por estrategia con las 4 métricas OOS relevantes para el catálogo.
    metricas_oos_subq = (
        select(
            MetricaEstrategia.id_estrategia.label("id_estrategia"),
            MetricaEstrategia.retorno_total.label("retorno_total_oos"),
            MetricaEstrategia.sharpe.label("sharpe_oos"),
            MetricaEstrategia.mdd.label("mdd_oos"),
            MetricaEstrategia.hit_rate.label("hit_rate_oos"),
        )
        .where(MetricaEstrategia.periodo == PeriodoEnum.OOS)
        .subquery()
    )

    stmt = (
        select(
            Estrategia,
            metricas_oos_subq.c.retorno_total_oos,
            metricas_oos_subq.c.sharpe_oos,
            metricas_oos_subq.c.mdd_oos,
            metricas_oos_subq.c.hit_rate_oos,
        )
        .outerjoin(metricas_oos_subq, metricas_oos_subq.c.id_estrategia == Estrategia.id)
        .order_by(Estrategia.id.asc())
    )
    if not incluir_benchmarks:
        stmt = stmt.where(Estrategia.tipo == TipoEstrategia.ESTRATEGIA_ACTIVA)
    if solo_activas:
        stmt = stmt.where(Estrategia.activa == True)  # noqa: E712
        stmt = stmt.where(Estrategia.estado == EstadoEstrategia.ACTIVA)

    results = []
    for row in db.execute(stmt).all():
        estrategia_orm = row[0]
        base = EstrategiaRead.model_validate(estrategia_orm)
        results.append(
            EstrategiaCatalogRead(
                **base.model_dump(),
                retorno_total_oos=row.retorno_total_oos,
                sharpe_oos=row.sharpe_oos,
                mdd_oos=row.mdd_oos,
                hit_rate_oos=row.hit_rate_oos,
            )
        )
    return results


def obtener_estrategia_por_id(
    db: Session,
    id_estrategia: int,
    solo_activas: bool = True,
) -> Optional[EstrategiaDetalleRead]:
    """Detalle de una estrategia con todas sus métricas (dev y oos) anidadas.

    Devuelve None si la estrategia no existe (o está inactiva cuando solo_activas=True).
    """
    stmt = select(Estrategia).where(Estrategia.id == id_estrategia)
    if solo_activas:
        stmt = stmt.where(Estrategia.activa == True)  # noqa: E712
    estrategia = db.scalar(stmt)
    if estrategia is None:
        return None

    # Carga las métricas de ambos periodos (dev y oos) ordenadas por periodo.
    metricas_orm = list(
        db.scalars(
            select(MetricaEstrategia)
            .where(MetricaEstrategia.id_estrategia == id_estrategia)
            .order_by(MetricaEstrategia.periodo)
        )
    )

    base = EstrategiaRead.model_validate(estrategia)
    return EstrategiaDetalleRead(
        **base.model_dump(),
        metricas=[MetricaEstrategiaRead.model_validate(m) for m in metricas_orm],
    )


def actualizar_estrategia(
    db: Session,
    id_estrategia: int,
    datos: EstrategiaUpdate,
) -> Optional[Estrategia]:
    """Aplica una actualización parcial (PATCH) sobre una estrategia existente.

    Carga la estrategia sin filtrar por activa para permitir editar también
    las dadas de baja. Devuelve None si no existe.
    Lanza ValueError si el nuevo nombre o código ya lo usa otra estrategia.
    """
    estrategia = db.scalar(select(Estrategia).where(Estrategia.id == id_estrategia))
    if estrategia is None:
        return None

    cambios = datos.model_dump(exclude_unset=True)

    if "nombre" in cambios and cambios["nombre"] != estrategia.nombre:
        conflicto = db.scalar(
            select(Estrategia).where(
                Estrategia.nombre == cambios["nombre"],
                Estrategia.id != id_estrategia,
            )
        )
        if conflicto is not None:
            raise ValueError(f"Ya existe una estrategia con el nombre '{cambios['nombre']}'.")

    if "codigo_estrategia" in cambios and cambios["codigo_estrategia"] != estrategia.codigo_estrategia:
        conflicto = db.scalar(
            select(Estrategia).where(
                Estrategia.codigo_estrategia == cambios["codigo_estrategia"],
                Estrategia.id != id_estrategia,
            )
        )
        if conflicto is not None:
            raise ValueError(f"Ya existe una estrategia con el código '{cambios['codigo_estrategia']}'.")

    for campo, valor in cambios.items():
        setattr(estrategia, campo, valor)

    db.commit()
    db.refresh(estrategia)
    return estrategia


def listar_estrategias_admin(db: Session) -> list[EstrategiaAdminRead]:
    """Devuelve TODAS las estrategias (activas e inactivas, estrategia_activa y benchmark)
    con conteo de contrataciones activas y fecha del dato más reciente en resultados (RF-12).

    Usa dos subqueries pre-agregadas independientes para evitar el producto
    cartesiano que se producía al hacer dos outerjoin directos sobre la misma
    fila base de Estrategia.
    """
    # Subquery 1: conteo de contrataciones ACTIVAS por estrategia.
    contrataciones_subq = (
        select(
            Contratacion.id_estrategia.label("id_estrategia"),
            func.count(Contratacion.id).label("num_activas"),
        )
        .where(Contratacion.estado == EstadoContratacion.ACTIVA)
        .group_by(Contratacion.id_estrategia)
        .subquery()
    )

    # Subquery 2: fecha del resultado más reciente por estrategia (cualquier periodo).
    resultados_subq = (
        select(
            ResultadoEstrategia.id_estrategia.label("id_estrategia"),
            func.max(ResultadoEstrategia.fecha).label("ultima_fecha"),
        )
        .group_by(ResultadoEstrategia.id_estrategia)
        .subquery()
    )

    stmt = (
        select(
            Estrategia,
            func.coalesce(contrataciones_subq.c.num_activas, 0).label("num_contrataciones_activas"),
            resultados_subq.c.ultima_fecha.label("fecha_ultima_actualizacion"),
        )
        .outerjoin(contrataciones_subq, contrataciones_subq.c.id_estrategia == Estrategia.id)
        .outerjoin(resultados_subq, resultados_subq.c.id_estrategia == Estrategia.id)
        .order_by(Estrategia.id.asc())
    )

    results = []
    for estrategia, num_activas, max_fecha in db.execute(stmt).all():
        base = EstrategiaRead.model_validate(estrategia)
        results.append(
            EstrategiaAdminRead(
                **base.model_dump(),
                num_contrataciones_activas=num_activas,
                fecha_ultima_actualizacion=max_fecha,
            )
        )
    return results


def dar_de_baja_estrategia(db: Session, id_estrategia: int) -> Optional[Estrategia]:
    """Realiza el soft delete de una estrategia y cancela todas sus contrataciones activas.

    Para cada contratación cancelada devuelve el monto_invertido al saldo_monedero
    del usuario propietario. Toda la operación es atómica (un único commit).
    Devuelve None si la estrategia no existe. Si ya estaba inactiva, la devuelve
    sin cambios (operación idempotente).
    """
    estrategia = db.scalar(select(Estrategia).where(Estrategia.id == id_estrategia))
    if estrategia is None:
        return None

    if not estrategia.activa:
        return estrategia

    cancelar_contrataciones_de_estrategia(db, estrategia.id)
    estrategia.activa = False

    db.commit()
    db.refresh(estrategia)
    return estrategia
