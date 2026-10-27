"""Separate the computer mouse from an existing animal vocabulary entry."""
from alembic import op
import sqlalchemy as sa
revision="0008_ai_senses"
down_revision="0007_reminders"
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    # Fresh/empty catalogs create this word on first capture. Repair existing
    # catalogs that already have a mouse, without rewriting that animal/history.
    if not bind.scalar(sa.text("SELECT count(*) FROM vocabularies WHERE lower(word)='mouse'")):
        return
    bind.execute(sa.text("""INSERT INTO vocabularies(word,ipa,part_of_speech,level,audio_url,created_at)
        VALUES('computer mouse','/maʊs/','noun','BEGINNER',
        'https://dict.youdao.com/dictvoice?audio=computer+mouse&type=2',now())
        ON CONFLICT(word) DO NOTHING"""))
    ident=bind.scalar(sa.text("SELECT vocabulary_id FROM vocabularies WHERE word='computer mouse'"))
    bind.execute(sa.text("""INSERT INTO vocabulary_meanings(vocabulary_id,meaning_vi)
        SELECT :v,'chuột máy tính' WHERE NOT EXISTS
        (SELECT 1 FROM vocabulary_meanings WHERE vocabulary_id=:v)"""),{"v":ident})
    bind.execute(sa.text("""INSERT INTO vocabulary_topics(vocabulary_id,topic_id)
        SELECT :v,topic_id FROM topics WHERE slug='objects' ON CONFLICT DO NOTHING"""),{"v":ident})

def downgrade():
    # Vocabulary may already be saved or reviewed. Preserve user references.
    pass
