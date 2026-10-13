"""Add server-controlled user/admin roles without granting existing accounts admin."""
from alembic import op
import sqlalchemy as sa
revision = "0005_admin_roles"
down_revision = "0004_learning"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("role", sa.String(10), nullable=False, server_default="USER"))
    op.create_check_constraint("users_role_check", "users", "role IN ('USER','ADMIN')")

def downgrade():
    op.drop_constraint("users_role_check", "users", type_="check")
    op.drop_column("users", "role")
