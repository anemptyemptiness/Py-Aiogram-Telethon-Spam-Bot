"""added column spam_msg_2 to table account

Revision ID: 2aa0da4f32e7
Revises: 151d8e54cb8c
Create Date: 2024-09-26 10:08:08.748310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2aa0da4f32e7'
down_revision: Union[str, None] = '151d8e54cb8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('account', sa.Column('spam_msg_2', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('account', 'spam_msg_2')
    # ### end Alembic commands ###
