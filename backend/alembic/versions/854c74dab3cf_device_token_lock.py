"""device_token_lock

Revision ID: 854c74dab3cf
Revises: c1f2b3145cbd
Create Date: 2026-07-11 12:28:42.431640

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '854c74dab3cf'
down_revision: Union[str, None] = 'c1f2b3145cbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('participants', sa.Column('device_token', sa.String(), nullable=True))
    op.create_index('ix_participants_poll_device', 'participants', ['poll_id', 'device_token'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_participants_poll_device', table_name='participants')
    op.drop_column('participants', 'device_token')
