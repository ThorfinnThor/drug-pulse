#!/usr/bin/env python3
"""
FDA Approvals ETL Script
Fetches FDA drug approvals from openFDA API and upserts into database
"""
import os
import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
import json

from db import get_db_connection 

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# OpenFDA API base URL
FDA_API_BASE = "https://api.fda.gov"
url = f"{FDA_API_BASE}/drug/drugsfda.json"

def fuzzy_match_drug(drug_name, conn):
    """Fuzzy match drug name to existing drug"""
    with conn.cursor() as cur:
        # Try exact match first
        cur.execute(
            """SELECT id FROM public.drugs 
               WHERE LOWER(preferred_name) = LOWER(%s) 
               OR LOWER(active_ingredient) = LOWER(%s)""",
            (drug_name, drug_name)
        )
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Try partial match
        cur.execute(
            """SELECT id FROM public.drugs 
               WHERE LOWER(preferred_name) LIKE LOWER(%s) 
               OR LOWER(active_ingredient) LIKE LOWER(%s)
               LIMIT 1""",
            (f"%{drug_name}%", f"%{drug_name}%")
        )
        result = cur.fetchone()
        if result:
            return result[0]
    
    return None

def fuzzy_match_indication(condition, conn):
    """Fuzzy match indication"""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id FROM public.indications 
               WHERE LOWER(label) LIKE LOWER(%s) 
               OR LOWER(description) LIKE LOWER(%s)
               LIMIT 1""",
            (f"%{condition}%", f"%{condition}%")
        )
        result = cur.fetchone()
        if result:
            return result[0]
    
    return None

def fetch_recent_approvals(days_back=30):
    """Fetch recent FDA drug approvals"""
    logger.info(f"Fetching FDA approvals from last {days_back} days...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Format dates for FDA API (YYYYMMDD)
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    
    url = f"{FDA_API_BASE}/drug/drugsfda.json"
    params = {
        'search': f'submissions.submission_date:[{start_date_str} TO {end_date_str}]',
        'limit': 1000
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        approvals = data.get('results', [])
        logger.info(f"Fetched {len(approvals)} FDA drug records")
        return approvals
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching FDA approvals: {str(e)}")
        return []

def upsert_approvals(approvals, conn):
    """Upsert approvals into database"""
    logger.info("Processing FDA approvals...")
    
    with conn.cursor() as cur:
        processed = 0
        
        for approval in approvals:
            try:
                # Extract drug information
                openfda = approval.get('openfda', {})
                brand_names = openfda.get('brand_name', [])
                generic_names = openfda.get('generic_name', [])
                
                # Use first available name
                drug_name = None
                if brand_names:
                    drug_name = brand_names[0]
                elif generic_names:
                    drug_name = generic_names[0]
                
                if not drug_name:
                    continue
                
                # Match to existing drug
                drug_id = fuzzy_match_drug(drug_name, conn)
                if not drug_id:
                    continue
                
                # Process submissions
                submissions = approval.get('submissions', [])
                for submission in submissions:
                    submission_date = submission.get('submission_date')
                    if not submission_date:
                        continue
                    
                    try:
                        approval_date = datetime.strptime(submission_date, '%Y%m%d').date()
                    except:
                        continue
                    
                    application_docs = submission.get('application_docs', [])
                    for doc in application_docs:
                        doc_url = doc.get('url', '')
                        doc_type = doc.get('type', '')
                        
                        if 'approval' in doc_type.lower():
                            # Insert approval record
                            cur.execute("""
                                INSERT INTO public.approvals 
                                (agency, approval_date, drug_id, document_url, application_number)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (
                                'FDA', approval_date, drug_id, doc_url,
                                approval.get('application_number', '')
                            ))
                            processed += 1
                            break
                
            except Exception as e:
                logger.warning(f"Error processing approval record: {str(e)}")
                continue
        
        conn.commit()
        logger.info(f"Processed {processed} FDA approval records")

def main():
    """Main ETL function"""
    try:
        conn = get_db_connection()
        logger.info("Connected to database")
        
        # Fetch recent approvals (default: 30 days)
        days_back = int(os.getenv('FDA_DAYS_BACK', '30'))
        approvals = fetch_recent_approvals(days_back)
        
        if approvals:
            upsert_approvals(approvals, conn)
            logger.info("FDA approvals ETL completed successfully!")
        else:
            logger.info("No approvals to process")
            
    except Exception as e:
        logger.error(f"ETL failed: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
