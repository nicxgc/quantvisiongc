"""Lógica de negocio para operaciones CRUD sobre la entidad Estrategia."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.contratacion import Contratacion, EstadoContratacion
from app.models.estrategia import Estrategia
from app.models.resultado_estrategia import ResultadoEstrategia
from app.schemas.estrategia import EstrategiaAdminRead, EstrategiaCreate, EstrategiaRead, EstrategiaUpdate
from app.services.contratacion_service import cancelar_contrataciones_de_estrategia


def crear_estrategia(db: Session, datos: EstrategiaCreate) -> Estrategia:
    """Crea una nueva estrategia tras verificar que el nombre no esté en uso.

    Lanza ValueError si ya existe una estrategia con el mismo nombre.
    """
    existente = db.scalar(select(Estrategia).where(Estrategia.nombre == datos.nombre))
    if existente is not None:
        raise ValueError(f"Ya existe una estrategia con el nombre '{datos.nombre}'.")

    estrategia = Estrategia(**datos.model_dump())
    db.add(estrategia)
    db.commit()
    db.refresh(estrategia)
    return estrategia


def listar_estrategias(db: Session, solo_activas: bool = True) -> list[Estrategia]:
    """Devuelve todas las estrategias ordenadas por id ascendente.

    Si solo_activas es True (por defecto), excluye las dadas de baja.
    """
    stmt = select(Estrategia).order_by(Estrategia.id)
    if solo_activas:
        stmt = stmt.where(Estrategia.activa == True)  # noqa: E712
    return list(db.scalars(stmt).all())


def obtener_estrategia_por_id(
    db: Session,
    id_estrategia: int,
    solo_activas: bool = True,
) -> Optional[Estrategia]:
    """Busca una estrategia por su id. Devuelve None si no se encuentra.

    Si solo_activas es True (por defecto), devuelve None también cuando
    la estrategia existe pero está dada de baja.
    """
    stmt = select(Estrategia).where(Estrategia.id == id_estrategia)
    if solo_activas:
        stmt = stmt.where(Estrategia.activa == True)  # noqa: E712
    return db.scalar(stmt)


def actualizar_estrategia(
    db: Session,
    id_estrategia: int,
    datos: EstrategiaUpdate,
) -> Optional[Estrategia]:
    """Aplica una actualización parcial (PATCH) sobre una estrategia existente.

    Carga la estrategia sin filtrar por activa para permitir editar también
    las dadas de baja. Devuelve None si no existe.
    Lanza ValueError si el nuevo nombre ya lo usa otra estrategia.
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

    for campo, valor in cambios.items():
        setattr(estrategia, campo, valor)

    db.commit()
    db.refresh(estrategia)
    return estrategia


def listar_estrategias_admin(db: Session) -> list[EstrategiaAdminRead]:
    """Devuelve TODAS las estrategias (activas e inactivas) con conteo de
    contrataciones activas y fecha del dato más reciente en resultados (RF-12).

    Usa dos subqueries pre-agregadas independientes para evitar el producto
    cartesiano que se producía al hacer dos outerjoin directos sobre la misma
    fila base de Estrategia. Cada subquery devuelve una sola fila por
    id_estrategia antes de unirse con la tabla principal.
    """
    # Subquery 1: conteo de contrataciones ACTIVAS por estrategia.
    # La condición de estado va dentro del subquery (WHERE interno),
    # nunca en la query externa, para no excluir estrategias con count=0.
    contrataciones_subq = (
        select(
            Contratacion.id_estrategia.label("id_estrategia"),
            func.count(Contratacion.id).label("num_activas"),
        )
        .where(Contratacion.estado == EstadoContratacion.ACTIVA)
        .group_by(Contratacion.id_estrategia)
        .subquery()
    )

    # Subquery 2: fecha del resultado más reciente por estrategia.
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
