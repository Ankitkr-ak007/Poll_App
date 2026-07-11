"""v3_schema

Revision ID: 9fc2b4163cbd
Revises: 8fc2b4163cba
Create Date: 2026-07-11 11:32:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9fc2b4163cbd'
down_revision: Union[str, None] = '8fc2b4163cba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add winner_option and final_counts to polls table
    op.add_column('polls', sa.Column('winner_option', sa.String(length=1), nullable=True))
    op.add_column('polls', sa.Column('final_counts', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Add indexes
    op.create_index('ix_participants_poll_status', 'participants', ['poll_id', 'has_voted'], unique=False)
    op.create_index('ix_vote_events_poll_time', 'vote_events', ['poll_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_vote_events_poll_time', table_name='vote_events')
    op.drop_index('ix_participants_poll_status', table_name='participants')
    op.drop_column('polls', 'final_counts')
    op.drop_column('polls', 'winner_option')
