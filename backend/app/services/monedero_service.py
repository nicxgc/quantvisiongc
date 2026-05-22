"""Lógica de negocio del monedero virtual: recargas e histórico de movimientos."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import CANTIDADES_RECARGA_PERMITIDAS
from app.models.movimiento_monedero import MovimientoMonedero, TipoMovimiento
from app.models.usuario import Usuario
from app.schemas.monedero import MonederoRecargaResponse, MovimientoMonederoRead


def registrar_movimiento(
    db: Session,
    usuario: Usuario,
    tipo: TipoMovimiento,
    monto: Decimal,
    id_contratacion: int | None = None,
) -> MovimientoMonedero:
    """Crea una fila en movimiento_monedero tomando el saldo ACTUAL del usuario como saldo_resultante.

    El caller debe haber actualizado ya usuario.saldo_monedero antes de llamar a esta
    función, porque saldo_resultante se lee del estado en sesión del objeto usuario.

    No hace commit: el caller decide cuándo cerrar la transacción.
    """
    movimiento = MovimientoMonedero(
        id_usuario=usuario.id,
        tipo=tipo,
        monto=monto,
        saldo_resultante=usuario.saldo_monedero,
        id_contratacion=id_contratacion,
    )
    db.add(movimiento)
    return movimiento


def ingresar(
    db: Session,
    id_usuario: int,
    cantidad: Decimal,
) -> MonederoRecargaResponse | None:
    """Recarga el monedero del usuario con una cantidad de las denominaciones permitidas.

    Devuelve None si el usuario no existe.
    Lanza ValueError si la cantidad no está en CANTIDADES_RECARGA_PERMITIDAS
    (defensa en profundidad; el validator Pydantic ya debería haber filtrado esto).

    Usa SELECT FOR UPDATE para evitar condiciones de carrera en la actualización del saldo.
    Toda la operación (saldo + movimiento) se confirma en un único commit atómico.
    """
    if cantidad not in CANTIDADES_RECARGA_PERMITIDAS:
        raise ValueError(
            f"La cantidad {cantidad} no está en las denominaciones permitidas."
        )

    usuario = db.execute(
        select(Usuario).where(Usuario.id == id_usuario).with_for_update()
    ).scalar_one_or_none()

    if usuario is None:
        return None

    saldo_anterior = usuario.saldo_monedero
    usuario.saldo_monedero += cantidad

    # flush hace visible el cambio de saldo dentro de la sesión antes
    # de que registrar_movimiento lea usuario.saldo_monedero.
    db.flush()

    movimiento = registrar_movimiento(db, usuario, TipoMovimiento.INGRESO, cantidad)
    db.commit()
    db.refresh(usuario)
    db.refresh(movimiento)

    return MonederoRecargaResponse(
        saldo_anterior=saldo_anterior,
        cantidad_ingresada=cantidad,
        saldo_actual=usuario.saldo_monedero,
        movimiento=MovimientoMonederoRead.model_validate(movimiento),
    )


def listar_movimientos(
    db: Session,
    id_usuario: int,
    limite: int,
    offset: int,
) -> list[MovimientoMonedero]:
    """Devuelve los movimientos del usuario ordenados por fecha DESC, con paginación por limite/offset."""
    stmt = (
        select(MovimientoMonedero)
        .where(MovimientoMonedero.id_usuario == id_usuario)
        .order_by(MovimientoMonedero.fecha.desc())
        .limit(limite)
        .offset(offset)
    )
    return list(db.scalars(stmt))
