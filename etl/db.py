# etl/db.py
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    conn = psycopg2.connect(
        host="db.wahqfdgybivndsplphro.supabase.co",  # force IPv4 resolution
        port=5432,
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        sslmode="require"  # required by Supabase
    )
    return conn
