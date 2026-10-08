"""Idempotent sample catalog for a newly migrated database."""
from sqlalchemy import text
from app.core.database import engine

SAMPLES = [
    ("cat", "/kæt/", "con mèo", "This is a cat.", "Đây là một con mèo.", "animals"),
    ("dog", "/dɒɡ/", "con chó", "The dog is friendly.", "Con chó rất thân thiện.", "animals"),
    ("apple", "/ˈæpəl/", "quả táo", "I eat an apple.", "Tôi ăn một quả táo.", "food"),
    ("car", "/kɑːr/", "ô tô", "This car is red.", "Chiếc ô tô này màu đỏ.", "objects"),
]

def main():
    created = 0
    with engine.begin() as c:
        for word, ipa, meaning, sentence, translation, slug in SAMPLES:
            topic_id = c.execute(text("SELECT topic_id FROM topics WHERE slug=:slug"), {"slug":slug}).scalar_one_or_none()
            if topic_id is None:
                raise RuntimeError("Run alembic upgrade head before seeding.")
            ids = c.execute(text("SELECT vocabulary_id FROM vocabularies WHERE lower(word)=:word"), {"word":word}).scalars().all()
            if not ids:
                ident = c.execute(text("INSERT INTO vocabularies(word,ipa,level) VALUES(:word,:ipa,'BEGINNER') RETURNING vocabulary_id"), {"word":word,"ipa":ipa}).scalar_one()
                c.execute(text("INSERT INTO vocabulary_meanings(vocabulary_id,meaning_vi) VALUES(:id,:meaning)"), {"id":ident,"meaning":meaning})
                c.execute(text("INSERT INTO vocabulary_examples(vocabulary_id,sentence_en,sentence_vi) VALUES(:id,:sentence,:translation)"), {"id":ident,"sentence":sentence,"translation":translation})
                ids = [ident]
                created += 1
            for ident in ids:
                c.execute(text("INSERT INTO vocabulary_topics(topic_id,vocabulary_id) VALUES(:topic,:word) ON CONFLICT DO NOTHING"), {"topic":topic_id,"word":ident})
    print(f"Created {created} sample words; existing vocabulary content preserved.")

if __name__ == "__main__": main()
