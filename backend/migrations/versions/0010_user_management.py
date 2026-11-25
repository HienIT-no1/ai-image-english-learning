"""Account locks and persistent revocation of sessions issued before a lock."""
from alembic import op
import sqlalchemy as sa

revision = "0010_user_management"
down_revision = "0009_word_defense"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM users WHERE is_locked OR auth_version > 0")):
        raise RuntimeError("Account restrictions exist; cannot discard revoked sessions by downgrading.")
    op.drop_column("users", "auth_version")
    op.drop_column("users", "is_locked")
