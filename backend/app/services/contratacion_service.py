from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contratacion import Contratacion, EstadoContratacion
from app.models.estrategia import Estrategia
from app.models.movimiento_monedero import TipoMovimiento
from app.models.usuario import Usuario
from app.schemas.contratacion import ContratacionCreate
from app.services.monedero_service import registrar_movimiento


def contratar_estrategia(
    db: Session,
    id_usuario: int,
    datos: ContratacionCreate,
) -> Optional[Contratacion]:
    """
    Contrata una estrategia para un usuario autenticado.

    Returns:
        - Contratacion creada si todo va bien.
        - None si la estrategia no existe o está inactiva.

    Raises:
        - ValueError("contratacion_activa_existente") si ya hay una
          contratación ACTIVA del mismo usuario sobre la misma estrategia.
        - ValueError("saldo_insuficiente") si el saldo no cubre el precio.
    """
    # 1. Estrategia existe y está activa.
    estrategia = db.get(Estrategia, datos.id_estrategia)
    if estrategia is None or not estrategia.activa:
        return None

    # 2. El usuario no tiene ya una contratación ACTIVA sobre esta
    #    misma estrategia.
    ya_contratada = db.execute(
        select(Contratacion).where(
            Contratacion.id_usuario == id_usuario,
            Contratacion.id_estrategia == datos.id_estrategia,
            Contratacion.estado == EstadoContratacion.ACTIVA,
        )
    ).scalar_one_or_none()
    if ya_contratada is not None:
        raise ValueError("contratacion_activa_existente")

    # 3. Cargar usuario con bloqueo de fila para evitar condiciones de
    #    carrera en el descuento de saldo.
    usuario = db.execute(
        select(Usuario).where(Usuario.id == id_usuario).with_for_update()
    ).scalar_one()

    # 4. Saldo suficiente.
    precio = estrategia.precio_subscripcion
    if usuario.saldo_monedero < precio:
        raise ValueError("saldo_insuficiente")

    # 5. Descontar saldo y crear contratación (misma transacción).
    usuario.saldo_monedero -= precio
    nueva = Contratacion(
        id_usuario=id_usuario,
        id_estrategia=datos.id_estrategia,
        monto_invertido=precio,
        fecha_contratacion=datetime.now(timezone.utc),
        estado=EstadoContratacion.ACTIVA,
    )
    db.add(nueva)
    # flush para que PostgreSQL asigne nueva.id antes de usarlo en el movimiento.
    db.flush()
    registrar_movimiento(db, usuario, TipoMovimiento.CONTRATACION, precio, nueva.id)
    db.commit()
    db.refresh(nueva)
    return nueva


def listar_contrataciones_usuario(
    db: Session,
    id_usuario: int,
) -> List[Contratacion]:
    """
    Lista todas las contrataciones de un usuario (activas y canceladas),
    ordenadas por fecha de contratación descendente.
    """
    return list(
        db.execute(
            select(Contratacion)
            .where(Contratacion.id_usuario == id_usuario)
            .order_by(Contratacion.fecha_contratacion.desc())
        ).scalars()
    )


def cancelar_contratacion(
    db: Session,
    id_contratacion: int,
    id_usuario: int,
) -> Optional[Contratacion]:
    """
    Cancela una contratación a petición del usuario propietario y le
    devuelve el monto_invertido al saldo_monedero.

    Returns:
        - Contratacion actualizada si todo va bien.
        - None si la contratación no existe o no pertenece al usuario
          (decisión de diseño: no filtramos existencia de IDs ajenos).

    Raises:
        - ValueError("contratacion_ya_cancelada") si la contratación ya
          estaba en estado CANCELADA.
    """
    contratacion = db.get(Contratacion, id_contratacion)
    if contratacion is None or contratacion.id_usuario != id_usuario:
        return None
    if contratacion.estado != EstadoContratacion.ACTIVA:
        raise ValueError("contratacion_ya_cancelada")

    _aplicar_cancelacion(db, contratacion)
    db.commit()
    db.refresh(contratacion)
    return contratacion


def _aplicar_cancelacion(db: Session, contratacion: Contratacion) -> None:
    """
    Helper interno: aplica la cancelación a una contratación ya
    verificada como ACTIVA, y devuelve el monto al saldo del usuario.

    No hace commit: el caller decide cuándo cerrar la transacción.
    Se reutiliza en dos escenarios:
      - cancelar_contratacion (cancelación individual por el usuario).
      - dar_de_baja_estrategia (cancelación en cascada cuando un admin
        desactiva una estrategia con contrataciones ACTIVAS) — Bloque 3.
    """
    usuario = db.execute(
        select(Usuario)
        .where(Usuario.id == contratacion.id_usuario)
        .with_for_update()
    ).scalar_one()
    usuario.saldo_monedero += contratacion.monto_invertido
    contratacion.estado = EstadoContratacion.CANCELADA
    contratacion.fecha_cancelacion = datetime.now(timezone.utc)
    registrar_movimiento(
        db, usuario, TipoMovimiento.CANCELACION,
        contratacion.monto_invertido, contratacion.id,
    )


def cancelar_contrataciones_de_usuario(db: Session, id_usuario: int) -> int:
    """
    Cancela todas las contrataciones ACTIVAS de un usuario y devuelve
    el monto_invertido al saldo_monedero del propio usuario.

    No hace commit: el caller (eliminar_usuario) garantiza la atomicidad
    cerrando la transacción una única vez.

    Returns:
        Número de contrataciones canceladas (0 si no había ninguna activa).
    """
    contrataciones = list(
        db.execute(
            select(Contratacion).where(
                Contratacion.id_usuario == id_usuario,
                Contratacion.estado == EstadoContratacion.ACTIVA,
            )
        ).scalars()
    )
    for contratacion in contrataciones:
        _aplicar_cancelacion(db, contratacion)
    return len(contrataciones)


def cancelar_contrataciones_de_estrategia(db: Session, id_estrategia: int) -> int:
    """
    Cancela todas las contrataciones ACTIVAS de una estrategia dada y
    devuelve el monto_invertido al saldo_monedero de cada usuario afectado.

    No hace commit: el caller (dar_de_baja_estrategia) garantiza la
    atomicidad cerrando la transacción una única vez.

    Returns:
        Número de contrataciones canceladas (0 si no había ninguna activa).
    """
    contrataciones = list(
        db.execute(
            select(Contratacion).where(
                Contratacion.id_estrategia == id_estrategia,
                Contratacion.estado == EstadoContratacion.ACTIVA,
            )
        ).scalars()
    )
    for contratacion in contrataciones:
        _aplicar_cancelacion(db, contratacion)
    return len(contrataciones)
