"""monedero recargable con historico de movimientos

Revision ID: 482b3608ec62
Revises: b6bd7d38713d
Create Date: 2026-05-22 10:52:54.523787

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '482b3608ec62'
down_revision: Union[str, None] = 'b6bd7d38713d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear la tabla movimiento_monedero.
    #    op.create_table gestiona automáticamente la creación del ENUM PostgreSQL
    #    'tipo_movimiento' antes de crear la tabla.
    op.create_table(
        'movimiento_monedero',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column(
            'tipo',
            sa.Enum('ingreso', 'contratacion', 'cancelacion', name='tipo_movimiento'),
            nullable=False,
        ),
        sa.Column('monto', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('saldo_resultante', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            'fecha',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('id_contratacion', sa.Integer(), nullable=True),
        sa.CheckConstraint('monto > 0', name='ck_movimiento_monto_positivo'),
        sa.ForeignKeyConstraint(['id_contratacion'], ['contratacion.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuario.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    # Índice compuesto (id_usuario, fecha) para histórico cronológico inverso por usuario (RF-47).
    op.create_index(
        'idx_movimiento_usuario_fecha',
        'movimiento_monedero',
        ['id_usuario', 'fecha'],
        unique=False,
    )

    # 2. Actualizar server_default de saldo_monedero de 10000.00 a 0.00.
    op.alter_column(
        'usuario',
        'saldo_monedero',
        server_default=sa.text("'0.00'"),
    )

    # 3. Resetear todos los saldos existentes a 0.
    op.execute("UPDATE usuario SET saldo_monedero = 0.00")

    # 4. Cancelar todas las contrataciones activas.
    #    Los saldos ya están en 0, no hay nada que devolver al monedero.
    op.execute(
        "UPDATE contratacion SET estado = 'cancelada', fecha_cancelacion = NOW() "
        "WHERE estado = 'activa'"
    )

    # Nota: el drop_index de resultado_estrategia_fecha_idx que autogenerate detecta
    # se omite intencionalmente: ese índice lo gestiona TimescaleDB y no debe tocarse.


def downgrade() -> None:
    # Nota: el downgrade no restaura los saldos previos ni las contrataciones
    # canceladas en el upgrade; esa información se pierde irreversiblemente.

    # 1. Revertir server_default de saldo_monedero a 10000.00.
    op.alter_column(
        'usuario',
        'saldo_monedero',
        server_default=sa.text("'10000.00'"),
    )

    # 2. Eliminar índice y tabla movimiento_monedero.
    op.drop_index('idx_movimiento_usuario_fecha', table_name='movimiento_monedero')
    op.drop_table('movimiento_monedero')

    # 3. Eliminar el tipo ENUM PostgreSQL.
    #    Debe ejecutarse DESPUÉS de drop_table porque PostgreSQL no permite
    #    borrar un tipo mientras está en uso por alguna columna.
    op.execute("DROP TYPE IF EXISTS tipo_movimiento")
