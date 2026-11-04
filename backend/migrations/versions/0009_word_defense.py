"""Add a second game without changing existing shooter decks or scores."""
from alembic import op
import sqlalchemy as sa
revision="0009_word_defense"
down_revision="0008_ai_senses"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("game_runs",sa.Column("learning_mode",sa.String(10),nullable=False,server_default="RECALL"))
    op.drop_constraint("game_runs_type_check","game_runs",type_="check")
    op.create_check_constraint("game_runs_type_check","game_runs","game_type IN ('WORD_SHOOTER','WORD_DEFENSE')")
    op.create_check_constraint("game_runs_mode_check","game_runs","learning_mode IN ('TYPING','RECALL')")

def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM game_runs WHERE game_type='WORD_DEFENSE'")):
        raise RuntimeError("Defense history exists; preserve it before downgrading.")
    op.drop_constraint("game_runs_mode_check","game_runs",type_="check")
    op.drop_constraint("game_runs_type_check","game_runs",type_="check")
    op.create_check_constraint("game_runs_type_check","game_runs","game_type='WORD_SHOOTER'")
    op.drop_column("game_runs","learning_mode")
