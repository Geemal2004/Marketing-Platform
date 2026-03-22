import os
import sqlalchemy
from pathlib import Path
from dotenv import load_dotenv

project_root = Path.cwd()
load_dotenv(project_root / ".env")

db_url = os.environ.get("DATABASE_URL")
if not db_url.startswith("postgres"):
    db_url = db_url.replace("postgres", "postgresql", 1)

print("Connecting to DB...")
engine = sqlalchemy.create_engine(db_url)
with engine.connect() as conn:
    results = conn.execute(sqlalchemy.text("SELECT column_name FROM information_schema.columns WHERE table_name='simulation_runs';")).fetchall()
    columns = [r[0] for r in results]
    print("Columns in simulation_runs:", columns)
    
    if "use_custom_agents_only" not in columns:
        print("ERROR: use_custom_agents_only is still missing from DB!")
    else:
        print("SUCCESS: use_custom_agents_only is present in DB.")
