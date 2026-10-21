"""Persist game sessions, rounds, and game learning events; preserve existing data."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
revision = "0006_word_shooter"
down_revision = "0005_admin_roles"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("game_runs",
        sa.Column("run_id",sa.BigInteger(),primary_key=True),
        sa.Column("user_id",sa.BigInteger(),sa.ForeignKey("users.user_id",ondelete="CASCADE"),nullable=False),
        sa.Column("client_session_id",pg.UUID(as_uuid=True),nullable=False),
        sa.Column("game_type",sa.String(30),nullable=False,server_default="WORD_SHOOTER"),
        sa.Column("source",sa.String(20),nullable=False),
        sa.Column("topic_id",sa.BigInteger(),nullable=True),
        sa.Column("pool",pg.JSONB(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.Column("completed_at",sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id","client_session_id",name="uq_game_user_session"),
        sa.CheckConstraint("source IN ('RANDOM','TOPIC','SAVED','DIFFICULT','REVIEW')",name="game_runs_source_check"),
        sa.CheckConstraint("game_type = 'WORD_SHOOTER'",name="game_runs_type_check"))
    op.create_table("game_rounds",
        sa.Column("round_id",sa.BigInteger(),primary_key=True),
        sa.Column("run_id",sa.BigInteger(),sa.ForeignKey("game_runs.run_id",ondelete="CASCADE"),nullable=False),
        sa.Column("sequence",sa.Integer(),nullable=False),
        sa.Column("stage",sa.Integer(),nullable=False),
        sa.Column("words",pg.JSONB(),nullable=False),
        sa.Column("results",pg.JSONB(),nullable=False,server_default=sa.text("'[]'::jsonb")),
        *[sa.Column(n,sa.Integer(),nullable=False,server_default="0") for n in ("correct_count","missed_count","max_combo","score")],
        sa.Column("status",sa.String(10),nullable=False,server_default="PLAYING"),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.Column("completed_at",sa.DateTime(timezone=True)),
        sa.UniqueConstraint("run_id","sequence",name="uq_game_round_sequence"),
        sa.CheckConstraint("status IN ('PLAYING','PASSED','FAILED')",name="game_rounds_status_check"),
        sa.CheckConstraint("stage > 0 AND sequence > 0",name="game_rounds_stage_check"),
        sa.CheckConstraint("correct_count >= 0 AND missed_count BETWEEN 0 AND 4 AND max_combo >= 0 AND score >= 0",name="game_rounds_counts_check"))
    op.drop_constraint("learning_events_kind_check","learning_events",type_="check")
    op.create_check_constraint("learning_events_kind_check","learning_events","kind IN ('FLASHCARD','QUIZ','GAME')")

def downgrade():
    # Refuse to remove game learning history silently.
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM learning_events WHERE kind='GAME'")):
        raise RuntimeError("Game learning history exists; back it up before downgrading.")
    op.drop_constraint("learning_events_kind_check","learning_events",type_="check")
    op.create_check_constraint("learning_events_kind_check","learning_events","kind IN ('FLASHCARD','QUIZ')")
    op.drop_table("game_rounds")
    op.drop_table("game_runs")
