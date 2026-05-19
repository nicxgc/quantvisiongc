"""add activa to usuario

Revision ID: b6bd7d38713d
Revises: 2c4820ed3953
Create Date: 2026-05-19 13:46:42.671479

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6bd7d38713d'
down_revision: Union[str, None] = '2c4820ed3953'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default=sa.true() es necesario para las filas existentes (NOT NULL sin valor).
    # El drop_index de resultado_estrategia_fecha_idx se omite intencionalmente:
    # ese índice lo gestiona TimescaleDB y no debe tocarse desde Alembic.
    op.add_column(
        'usuario',
        sa.Column('activa', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column('usuario', 'activa')
