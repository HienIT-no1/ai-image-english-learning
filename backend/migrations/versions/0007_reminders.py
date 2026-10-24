"""Daily reminder time, review intervals and per-user notification inbox."""
from alembic import op
import sqlalchemy as sa
revision="0007_reminders"
down_revision="0006_word_shooter"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("users",sa.Column("reminder_minutes",sa.Integer(),nullable=False,server_default="1200"))
    op.create_check_constraint("users_reminder_minutes_check","users","reminder_minutes BETWEEN 0 AND 1439")
    op.add_column("learning_progress",sa.Column("review_interval_days",sa.Integer(),nullable=False,server_default="0"))
    op.create_check_constraint("learning_progress_interval_check","learning_progress","review_interval_days BETWEEN 0 AND 30")
    op.execute("""UPDATE learning_progress SET
        next_review_at=CASE WHEN status='MASTERED' THEN COALESCE(last_reviewed_at,now())+interval '7 days'
                            ELSE COALESCE(last_reviewed_at,now()) END,
        review_interval_days=CASE WHEN status='MASTERED' THEN 7 ELSE 0 END
        WHERE next_review_at IS NULL""")
    op.create_index("ix_learning_progress_user_due","learning_progress",["user_id","next_review_at"])
    op.create_table("notifications",
        sa.Column("notification_id",sa.BigInteger(),primary_key=True),
        sa.Column("user_id",sa.BigInteger(),sa.ForeignKey("users.user_id",ondelete="CASCADE"),nullable=False),
        sa.Column("occurrence_date",sa.Date(),nullable=False),
        sa.Column("title",sa.String(180),nullable=False),
        sa.Column("body",sa.String(500),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.Column("read_at",sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id","occurrence_date",name="uq_notification_user_day"))
    op.create_index("ix_notifications_user_created","notifications",["user_id","created_at"])

def downgrade():
    op.drop_table("notifications")
    op.drop_index("ix_learning_progress_user_due",table_name="learning_progress")
    op.drop_constraint("learning_progress_interval_check","learning_progress",type_="check")
    op.drop_column("learning_progress","review_interval_days")
    op.drop_constraint("users_reminder_minutes_check","users",type_="check")
    op.drop_column("users","reminder_minutes")
