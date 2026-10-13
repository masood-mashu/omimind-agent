import os

import psycopg
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL')
with psycopg.connect(db_url) as conn:
    cols = conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'omi_connections'").fetchall()
    col_names = [c[0] for c in cols]
    print('Existing columns:', col_names)
    if 'rotated_at' not in col_names:
        print("Adding 'rotated_at' column to omi_connections table...")
        conn.execute("ALTER TABLE omi_connections ADD COLUMN IF NOT EXISTS rotated_at DOUBLE PRECISION")
        conn.commit()
        print("Column 'rotated_at' added successfully!")
    else:
        print("'rotated_at' already exists.")
