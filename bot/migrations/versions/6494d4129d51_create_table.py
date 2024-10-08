"""create table

Revision ID: 6494d4129d51
Revises: 
Create Date: 2024-09-11 19:20:54.114302

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6494d4129d51'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('account',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('api_id', sa.Integer(), nullable=False),
    sa.Column('api_hash', sa.String(), nullable=False),
    sa.Column('phone', sa.String(), nullable=False),
    sa.Column('fa2', sa.String(), nullable=True),
    sa.Column('db_name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('api_hash'),
    sa.UniqueConstraint('api_id'),
    sa.UniqueConstraint('db_name'),
    sa.UniqueConstraint('phone')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('account')
    # ### end Alembic commands ###
