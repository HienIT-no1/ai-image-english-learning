"""Persist profile, practice events and resumable server-scored quizzes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0004_learning"
down_revision="0003_collection"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("users",sa.Column("cefr_level",sa.String(2),nullable=True))
    op.add_column("users",sa.Column("reminders_enabled",sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column("users",sa.Column("onboarding_completed",sa.Boolean(),nullable=False,server_default=sa.false()))
    op.execute("UPDATE users SET cefr_level=CASE english_level WHEN 'BEGINNER' THEN 'A1' WHEN 'INTERMEDIATE' THEN 'B1' WHEN 'ADVANCED' THEN 'B2' END, onboarding_completed=(english_level IS NOT NULL)")
    op.create_check_constraint("users_cefr_level_check","users","cefr_level IN ('A1','A2','B1','B2')")
    op.create_table("learning_events",
        sa.Column("event_id",sa.BigInteger(),primary_key=True),
        sa.Column("user_id",sa.BigInteger(),sa.ForeignKey("users.user_id",ondelete="CASCADE"),nullable=False),
        sa.Column("vocabulary_id",sa.BigInteger(),sa.ForeignKey("vocabularies.vocabulary_id",ondelete="CASCADE"),nullable=False),
        sa.Column("event_key",postgresql.UUID(as_uuid=True),nullable=False),
        sa.Column("kind",sa.String(20),nullable=False),
        sa.Column("is_correct",sa.Boolean(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.UniqueConstraint("user_id","event_key",name="uq_learning_event_user_key"),
        sa.CheckConstraint("kind IN ('FLASHCARD','QUIZ')",name="learning_events_kind_check"))
    op.create_index("ix_learning_events_user_date","learning_events",["user_id","created_at"])
    op.add_column("quiz_attempts",sa.Column("client_session_id",postgresql.UUID(as_uuid=True),nullable=True))
    op.add_column("quiz_attempts",sa.Column("question_payload",postgresql.JSONB(),nullable=False,server_default=sa.text("'{}'::jsonb")))
    op.add_column("quiz_attempts",sa.Column("aborted_at",sa.DateTime(timezone=True),nullable=True))
    op.create_unique_constraint("uq_quiz_user_session","quiz_attempts",["user_id","client_session_id"])
    op.create_index("ix_quiz_attempts_user_completed","quiz_attempts",["user_id","completed_at"])
    op.add_column("quiz_answers",sa.Column("question_id",sa.String(36),nullable=True))
    op.add_column("quiz_answers",sa.Column("question_index",sa.Integer(),nullable=True))
    op.create_unique_constraint("uq_quiz_answer_question","quiz_answers",["attempt_id","question_id"])
    op.create_unique_constraint("uq_quiz_answer_index","quiz_answers",["attempt_id","question_index"])

def downgrade():
    op.drop_constraint("uq_quiz_answer_index","quiz_answers",type_="unique")
    op.drop_constraint("uq_quiz_answer_question","quiz_answers",type_="unique")
    op.drop_column("quiz_answers","question_index")
    op.drop_column("quiz_answers","question_id")
    op.drop_index("ix_quiz_attempts_user_completed",table_name="quiz_attempts")
    op.drop_constraint("uq_quiz_user_session","quiz_attempts",type_="unique")
    for column in ["aborted_at","question_payload","client_session_id"]: op.drop_column("quiz_attempts",column)
    op.drop_table("learning_events")
    op.drop_constraint("users_cefr_level_check","users",type_="check")
    for column in ["onboarding_completed","reminders_enabled","cefr_level"]: op.drop_column("users",column)
