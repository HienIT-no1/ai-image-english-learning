from alembic import context
from sqlalchemy import create_engine, pool
from app.core.config import settings
from app.core.database import Base
import app.models

# Only fully mapped tables in the implemented flows are managed by autogenerate.
# Existing legacy tables remain managed by the baseline SQL until mapped fully.
MANAGED_TABLES = {"topics", "vocabulary_topics", "collections", "collection_words", "learning_progress", "learning_events", "quiz_attempts", "quiz_answers"}
def include_name(name, type_, parent_names):
    return type_ != "table" or name in MANAGED_TABLES

def include_object(obj, name, type_, reflected, compare_to):
    table = obj if type_ == "table" else getattr(obj, "table", None)
    return table is None or table.name in MANAGED_TABLES

if context.is_offline_mode():
    raise RuntimeError("These migrations validate existing PostgreSQL schemas; run them online.")
engine = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata,
                      include_name=include_name, include_object=include_object,
                      compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
