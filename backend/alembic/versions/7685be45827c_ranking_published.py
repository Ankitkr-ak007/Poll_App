"""ranking_published

Revision ID: 7685be45827c
Revises: 854c74dab3cf
Create Date: 2026-07-11 12:43:29.971395

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7685be45827c'
down_revision: Union[str, None] = '854c74dab3cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sessions', sa.Column('ranking_published', sa.Boolean(), server_default='false', nullable=True))


def downgrade() -> None:
    op.drop_column('sessions', 'ranking_published')
