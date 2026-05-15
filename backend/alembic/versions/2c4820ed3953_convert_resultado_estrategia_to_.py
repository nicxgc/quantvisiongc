"""convert resultado_estrategia to hypertable

Revision ID: 2c4820ed3953
Revises: bc3f4b90342a
Create Date: 2026-05-15 12:06:48.325882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c4820ed3953'
down_revision: Union[str, None] = 'bc3f4b90342a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "SELECT create_hypertable("
        "'resultado_estrategia', "
        "'fecha', "
        "chunk_time_interval => INTERVAL '1 month', "
        "if_not_exists => TRUE);"
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Convertir una hypertable de vuelta a tabla regular no es una "
        "operación soportada directamente por TimescaleDB. En caso de "
        "necesidad, recrear la tabla manualmente."
    )
