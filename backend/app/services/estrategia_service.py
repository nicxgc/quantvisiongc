"""Lógica de negocio para operaciones CRUD sobre la entidad Estrategia."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contratacion import Contratacion, EstadoContratacion
from app.models.estrategia import Estrategia
from app.models.usuario import Usuario
from app.schemas.estrategia import EstrategiaCreate, EstrategiaUpdate


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

    contrataciones_activas = list(
        db.scalars(
            select(Contratacion).where(
                Contratacion.id_estrategia == id_estrategia,
                Contratacion.estado == EstadoContratacion.ACTIVA,
            )
        ).all()
    )

    ahora = datetime.now(timezone.utc)

    for contratacion in contrataciones_activas:
        contratacion.estado = EstadoContratacion.CANCELADA
        contratacion.fecha_cancelacion = ahora
        usuario: Usuario = contratacion.usuario
        usuario.saldo_monedero += contratacion.monto_invertido

    estrategia.activa = False

    db.commit()
    db.refresh(estrategia)
    return estrategia
