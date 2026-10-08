"""One default collection per user; retain all existing collections and words."""
from alembic import op
import sqlalchemy as sa
revision = "0003_collection"
down_revision = "0002_topics"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("collections", sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE collections SET is_default=true WHERE collection_id IN (SELECT min(collection_id) FROM collections GROUP BY user_id)")
    op.create_index("uq_collections_default_user", "collections", ["user_id"], unique=True, postgresql_where=sa.text("is_default"))
    op.create_index("ix_collections_user_id", "collections", ["user_id"])
    # Present a user's existing saved words in the default library without deleting old collections.
    op.execute("""INSERT INTO collection_words(collection_id,vocabulary_id,image_id,added_at)
        SELECT DISTINCT ON (d.collection_id,w.vocabulary_id) d.collection_id,w.vocabulary_id,w.image_id,w.added_at
        FROM collections d JOIN collections source ON source.user_id=d.user_id
        JOIN collection_words w ON w.collection_id=source.collection_id WHERE d.is_default
        ORDER BY d.collection_id,w.vocabulary_id,w.added_at
        ON CONFLICT(collection_id,vocabulary_id) DO NOTHING""")

def downgrade():
    op.drop_index("ix_collections_user_id", table_name="collections")
    op.drop_index("uq_collections_default_user", table_name="collections")
    op.drop_column("collections", "is_default")
