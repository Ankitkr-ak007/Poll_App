"""roster_roundvote

Revision ID: d92309becb4b
Revises: 7685be45827c
Create Date: 2026-07-11 13:06:09.066073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd92309becb4b'
down_revision: Union[str, None] = '7685be45827c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('roster',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), sa.ForeignKey('sessions.id')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('vote_code', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'name', name='uq_session_name'),
        sa.UniqueConstraint('vote_code', name='uq_vote_code')
    )
    
    op.create_table('round_votes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('poll_id', sa.UUID(), sa.ForeignKey('polls.id')),
        sa.Column('roster_id', sa.UUID(), sa.ForeignKey('roster.id')),
        sa.Column('has_voted', sa.Boolean(), server_default='false'),
        sa.Column('voted_option', sa.String(length=1), nullable=True),
        sa.Column('voted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_vote_attempt_id', sa.String(), nullable=True),
        sa.Column('device_token', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('poll_id', 'roster_id', name='uq_poll_roster')
    )
    
    op.create_index('ix_round_votes_poll_status', 'round_votes', ['poll_id', 'has_voted'])
    op.create_index('ix_round_votes_poll_device', 'round_votes', ['poll_id', 'device_token'])

    # Dropping old participants table
    op.drop_table('participants')

def downgrade() -> None:
    pass
