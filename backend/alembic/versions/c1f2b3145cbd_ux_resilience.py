"""ux_resilience_last_vote_attempt_id

Revision ID: c1f2b3145cbd
Revises: 9fc2b4163cbd
Create Date: 2026-07-11 11:51:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c1f2b3145cbd'
down_revision = '9fc2b4163cbd'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add last_vote_attempt_id to participants
    op.add_column('participants', sa.Column('last_vote_attempt_id', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('participants', 'last_vote_attempt_id')
