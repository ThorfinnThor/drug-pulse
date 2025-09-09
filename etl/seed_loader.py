#!/usr/bin/env python3
"""
Seed data loader for PharmaIntel
Loads CSV files into Postgres database
"""
import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection from environment variables"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db.wahqfdgybivndsplphro.supabase.co'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'postgres'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )

def load_companies(conn):
    """Load companies from CSV"""
    logger.info("Loading companies...")
    df = pd.read_csv('seed/companies.csv')
    
    with conn.cursor() as cur:
        # Clear existing data
        cur.execute("TRUNCATE public.companies CASCADE")
        
        # Insert new data
        values = [tuple(row) for row in df.values]
        execute_values(
            cur,
            """INSERT INTO public.companies 
               (canonical_name, cik, country, website, ticker, market_cap) 
               VALUES %s""",
            values
        )
        conn.commit()
        logger.info(f"Loaded {len(df)} companies")

def load_indications(conn):
    """Load indications from CSV"""
    logger.info("Loading indications...")
    df = pd.read_csv('seed/indications.csv')
    
    with conn.cursor() as cur:
        cur.execute("TRUNCATE public.indications CASCADE")
        
        values = [tuple(row) for row in df.values]
        execute_values(
            cur,
            """INSERT INTO public.indications 
               (label, mesh_id, icd10, description) 
               VALUES %s""",
            values
        )
        conn.commit()
        logger.info(f"Loaded {len(df)} indications")

def load_drugs(conn):
    """Load drugs from CSV"""
    logger.info("Loading drugs...")
    df = pd.read_csv('seed/drugs.csv')
    
    with conn.cursor() as cur:
        cur.execute("TRUNCATE public.drugs CASCADE")
        
        values = [tuple(row) for row in df.values]
        execute_values(
            cur,
            """INSERT INTO public.drugs 
               (preferred_name, active_ingredient, mechanism, company_id) 
               VALUES %s""",
            values
        )
        conn.commit()
        logger.info(f"Loaded {len(df)} drugs")

def load_trials(conn):
    """Load trials from CSV"""
    logger.info("Loading trials...")
    df = pd.read_csv('seed/trials.csv')
    
    with conn.cursor() as cur:
        cur.execute("TRUNCATE public.trials CASCADE")
        
        values = [tuple(row) for row in df.values]
        execute_values(
            cur,
            """INSERT INTO public.trials 
               (id, title, phase, status, start_date, primary_completion_date, sponsor_company_id) 
               VALUES %s""",
            values
        )
        conn.commit()
        logger.info(f"Loaded {len(df)} trials")

def load_trial_indications(conn):
    """Load trial-indication relationships from CSV"""
    logger.info("Loading trial-indication relationships...")
    df = pd.read_csv('seed/trial_indications.csv')
    
    with conn.cursor() as cur:
        cur.execute("TRUNCATE public.trial_indications CASCADE")
        
        values = [tuple(row) for row in df.values]
        execute_values(
            cur,
            """INSERT INTO public.trial_indications 
               (trial_id, indication_id) 
               VALUES %s""",
            values
        )
        conn.commit()
        logger.info(f"Loaded {len(df)} trial-indication relationships")

def refresh_search_view(conn):
    """Refresh the search materialized view"""
    logger.info("Refreshing search materialized view...")
    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW public.search_mv")
        conn.commit()
        logger.info("Search view refreshed")

def main():
    """Main seed loading function"""
    try:
        conn = get_db_connection()
        logger.info("Connected to database")
        
        # Load data in dependency order
        load_companies(conn)
        load_indications(conn)
        load_drugs(conn)
        load_trials(conn)
        load_trial_indications(conn)
        
        # Refresh search view
        refresh_search_view(conn)
        
        logger.info("Seed data loading completed successfully!")
        
    except Exception as e:
        logger.error(f"Error loading seed data: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()