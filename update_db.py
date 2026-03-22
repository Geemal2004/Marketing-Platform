import os
import sqlalchemy
from pathlib import Path
from dotenv import load_dotenv

project_root = Path.cwd()
load_dotenv(project_root / ".env")

db_url = os.environ.get("DATABASE_URL")
if not db_url.startswith("postgres"):
    db_url = db_url.replace("postgres", "postgresql", 1)

print("Connecting to DB:", db_url)
engine = sqlalchemy.create_engine(db_url)
with engine.connect() as conn:
    print("Executing migration 004_custom_agents.sql...")
    with open("database/migrations/004_custom_agents.sql", "r") as f:
        sql = f.read()
    
    # Execute split statements since some backends can't handle multiple statements in one execute call
    for statement in sql.split(";"):
        if statement.strip():
            conn.execute(sqlalchemy.text(statement.strip()))
            conn.commit()
    print("Migration executed successfully!")
    
    # Verify
    results = conn.execute(sqlalchemy.text("SELECT column_name FROM information_schema.columns WHERE table_name='simulation_runs';")).fetchall()
    print("Columns in simulation_runs:", [r[0] for r in results])
