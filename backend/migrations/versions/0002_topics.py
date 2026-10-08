"""Add topic catalog and classify existing vocabulary."""
from alembic import op
import sqlalchemy as sa
revision = "0002_topics"
down_revision = "0001_legacy"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("topics",
        sa.Column("topic_id", sa.BigInteger(), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("vocabulary_topics",
        sa.Column("topic_id", sa.BigInteger(), sa.ForeignKey("topics.topic_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("vocabulary_id", sa.BigInteger(), sa.ForeignKey("vocabularies.vocabulary_id", ondelete="CASCADE"), primary_key=True))
    op.create_index("ix_vocabulary_topics_vocabulary_id", "vocabulary_topics", ["vocabulary_id"])
    topics = sa.table("topics", sa.column("slug"), sa.column("name"), sa.column("symbol"))
    op.bulk_insert(topics, [
        {"slug": "animals", "name": "Động vật", "symbol": "🐾"},
        {"slug": "food", "name": "Đồ ăn", "symbol": "🍎"},
        {"slug": "objects", "name": "Đồ vật", "symbol": "📦"},
        {"slug": "places", "name": "Địa điểm", "symbol": "🏙️"},
        {"slug": "nature", "name": "Thiên nhiên", "symbol": "🌿"},
        {"slug": "adjectives", "name": "Tính từ", "symbol": "✨"},
    ])
    mapping = {"animals": ["cat", "dog"], "food": ["apple"],
        "objects": ["car", "computer"], "places": ["bank"],
        "nature": ["rain"], "adjectives": ["beautiful", "pretty", "ugly"]}
    for slug, words in mapping.items():
        for word in words:
            op.get_bind().execute(sa.text("""INSERT INTO vocabulary_topics (topic_id, vocabulary_id)
                SELECT t.topic_id, v.vocabulary_id FROM topics t CROSS JOIN vocabularies v
                WHERE t.slug = :slug AND lower(v.word) = :word"""), {"slug": slug, "word": word})

def downgrade():
    op.drop_table("vocabulary_topics")
    op.drop_table("topics")
