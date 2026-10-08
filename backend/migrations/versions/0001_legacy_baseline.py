"""Create the legacy schema on a new DB, or validate/adopt an existing one."""
import json
from pathlib import Path
from alembic import op
import sqlalchemy as sa
revision = "0001_legacy"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    inspector = sa.inspect(op.get_bind())
    folder = Path(__file__).parent
    expected = json.loads((folder / "0001_columns.json").read_text(encoding="utf-8"))
    existing = set(inspector.get_table_names()) - {"alembic_version"}
    if existing:
        problems = []
        for table, columns in expected.items():
            if table not in existing:
                problems.append(f"missing table {table}")
            else:
                found = {c["name"] for c in inspector.get_columns(table)}
                missing = set(columns) - found
                if missing:
                    problems.append(f"{table}: missing columns {sorted(missing)}")
        if problems:
            raise RuntimeError("Cannot adopt partial legacy schema: " + "; ".join(problems))
        return  # Existing rows, sequences and tables are preserved.
    sql = (folder / "0001_schema.sql").read_text(encoding="utf-8")
    sql = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(sa.text(statement))

def downgrade():
    # Never erase a legacy schema that may have been adopted with existing data.
    raise RuntimeError("Legacy baseline cannot be downgraded; restore a backup if required.")
