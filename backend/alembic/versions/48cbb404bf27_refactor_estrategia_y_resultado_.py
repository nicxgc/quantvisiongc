"""Refactor estrategia y resultado_estrategia, introduce metrica_estrategia para soporte dev_oos

Revision ID: 48cbb404bf27
Revises: 482b3608ec62
Create Date: 2026-05-23 12:47:45.642561

Cambios manuales sobre el autogenerate:
  1. Los ENUMs periodo_enum y tipo_estrategia_enum se crean explícitamente con CREATE TYPE
     antes de usarlos (create_type=False en los modelos impide que create_table los cree solo).
  2. resultado_estrategia se reconstruye completa (drop + create + create_hypertable) porque
     TimescaleDB no admite ALTER PRIMARY KEY en hypertables.
  3. Eliminada la línea `drop_index('resultado_estrategia_fecha_idx')` —TimescaleDB gestiona
     ese índice internamente y su eliminación provocaría un error.
  4. Nombre explícito para el unique constraint de codigo_estrategia.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '48cbb404bf27'
down_revision: Union[str, None] = '482b3608ec62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Crear tipos ENUM nativos de PostgreSQL ANTES de usarlos en columnas.
    #    Los modelos usan create_type=False, así que Alembic no los crea solo.
    # -------------------------------------------------------------------------
    op.execute("CREATE TYPE periodo_enum AS ENUM ('dev', 'oos')")
    op.execute("CREATE TYPE tipo_estrategia_enum AS ENUM ('estrategia_activa', 'benchmark')")

    # -------------------------------------------------------------------------
    # 2. Crear tabla metrica_estrategia (nueva en T1.1).
    # -------------------------------------------------------------------------
    op.create_table(
        'metrica_estrategia',
        sa.Column('id_estrategia', sa.Integer(), nullable=False),
        sa.Column('periodo', postgresql.ENUM('dev', 'oos', name='periodo_enum', create_type=False), nullable=False),
        sa.Column('fecha_inicio_periodo', sa.Date(), nullable=False),
        sa.Column('fecha_fin_periodo', sa.Date(), nullable=False),
        sa.Column('retorno_total', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('cagr', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('volatility', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('sharpe', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('sortino', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('calmar', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('mdd', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('n_trades', sa.Integer(), nullable=True),
        sa.Column('hit_rate', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('profit_factor', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.ForeignKeyConstraint(['id_estrategia'], ['estrategia.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_estrategia', 'periodo', name='pk_metrica_estrategia'),
    )

    # -------------------------------------------------------------------------
    # 3. Modificar tabla estrategia: añadir 3 columnas nuevas + borrar 13 obsoletas.
    #    Las tablas están vacías (truncadas antes de esta migración), así que
    #    NOT NULL en codigo_estrategia y tipo no requiere valor por defecto.
    # -------------------------------------------------------------------------
    op.add_column('estrategia', sa.Column('codigo_estrategia', sa.String(length=50), nullable=False))
    op.add_column('estrategia', sa.Column(
        'tipo',
        postgresql.ENUM('estrategia_activa', 'benchmark', name='tipo_estrategia_enum', create_type=False),
        nullable=False,
    ))
    op.add_column('estrategia', sa.Column('fecha_fin', sa.Date(), nullable=True))
    op.create_unique_constraint('uq_estrategia_codigo_estrategia', 'estrategia', ['codigo_estrategia'])

    # Eliminar los 13 campos de métricas/escenarios movidos a metrica_estrategia
    op.drop_column('estrategia', 'retorno_total')
    op.drop_column('estrategia', 'volatilidad')
    op.drop_column('estrategia', 'max_drawdown')
    op.drop_column('estrategia', 'win_rate')
    op.drop_column('estrategia', 'sortino_ratio')
    op.drop_column('estrategia', 'sharpe_ratio')
    op.drop_column('estrategia', 'num_operaciones')
    op.drop_column('estrategia', 'mejor_1m')
    op.drop_column('estrategia', 'peor_1m')
    op.drop_column('estrategia', 'mejor_3m')
    op.drop_column('estrategia', 'peor_3m')
    op.drop_column('estrategia', 'mejor_1a')
    op.drop_column('estrategia', 'peor_1a')

    # -------------------------------------------------------------------------
    # 4. Reconstruir resultado_estrategia como hypertable con nueva PK.
    #    TimescaleDB no permite ALTER PRIMARY KEY en hypertables, por lo que
    #    es obligatorio hacer drop + create + create_hypertable.
    #    NOTA: NO se incluye drop_index('resultado_estrategia_fecha_idx') porque
    #    ese índice es gestionado por TimescaleDB internamente.
    # -------------------------------------------------------------------------
    op.drop_table('resultado_estrategia')

    op.create_table(
        'resultado_estrategia',
        sa.Column('id_estrategia', sa.Integer(), nullable=False),
        sa.Column('periodo', postgresql.ENUM('dev', 'oos', name='periodo_enum', create_type=False), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('equity', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('drawdown', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('retorno', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.ForeignKeyConstraint(['id_estrategia'], ['estrategia.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_estrategia', 'periodo', 'fecha', name='pk_resultado_estrategia'),
    )
    op.execute(
        "SELECT create_hypertable('resultado_estrategia', 'fecha', "
        "if_not_exists => TRUE, migrate_data => TRUE)"
    )


def downgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Reconstruir resultado_estrategia con el esquema anterior (PK sin periodo).
    # -------------------------------------------------------------------------
    op.drop_table('resultado_estrategia')

    op.create_table(
        'resultado_estrategia',
        sa.Column('id_estrategia', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('equity', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('drawdown', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('retorno', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('sharpe_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.ForeignKeyConstraint(['id_estrategia'], ['estrategia.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_estrategia', 'fecha', name='pk_resultado_estrategia'),
    )
    op.execute(
        "SELECT create_hypertable('resultado_estrategia', 'fecha', "
        "if_not_exists => TRUE, migrate_data => TRUE)"
    )

    # -------------------------------------------------------------------------
    # 2. Revertir columnas de estrategia.
    # -------------------------------------------------------------------------
    op.drop_constraint('uq_estrategia_codigo_estrategia', 'estrategia', type_='unique')
    op.drop_column('estrategia', 'fecha_fin')
    op.drop_column('estrategia', 'tipo')
    op.drop_column('estrategia', 'codigo_estrategia')

    # Restaurar las 13 columnas de métricas (todas nullable para no romper filas existentes)
    op.add_column('estrategia', sa.Column('retorno_total', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('estrategia', sa.Column('volatilidad', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('estrategia', sa.Column('max_drawdown', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('estrategia', sa.Column('win_rate', sa.Numeric(precision=5, scale=4), nullable=True))
    op.add_column('estrategia', sa.Column('sortino_ratio', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('estrategia', sa.Column('sharpe_ratio', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('estrategia', sa.Column('num_operaciones', sa.Integer(), nullable=True))
    op.add_column('estrategia', sa.Column('mejor_1m', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('estrategia', sa.Column('peor_1m', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('estrategia', sa.Column('mejor_3m', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('estrategia', sa.Column('peor_3m', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('estrategia', sa.Column('mejor_1a', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('estrategia', sa.Column('peor_1a', sa.Numeric(precision=10, scale=4), nullable=True))

    # -------------------------------------------------------------------------
    # 3. Eliminar tabla metrica_estrategia.
    # -------------------------------------------------------------------------
    op.drop_table('metrica_estrategia')

    # -------------------------------------------------------------------------
    # 4. Eliminar los tipos ENUM creados en upgrade.
    # -------------------------------------------------------------------------
    op.execute("DROP TYPE IF EXISTS tipo_estrategia_enum")
    op.execute("DROP TYPE IF EXISTS periodo_enum")
