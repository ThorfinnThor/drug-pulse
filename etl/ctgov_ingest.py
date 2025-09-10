#!/usr/bin/env python3
"""
ClinicalTrials.gov ETL Script
Fetches recent studies from ClinicalTrials.gov API v2 and upserts into database
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

# ClinicalTrials.gov API v2 base URL
CTGOV_API_BASE = "https://clinicaltrials.gov/api/v2"

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db.wahqfdgybivndsplphro.supabase.co'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'postgres'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )

def fuzzy_match_company(sponsor_name, conn):
    """Fuzzy match sponsor name to existing company"""
    with conn.cursor() as cur:
        # First try exact match
        cur.execute(
            "SELECT id FROM public.companies WHERE LOWER(canonical_name) = LOWER(%s)",
            (sponsor_name,)
        )
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Try partial match
        cur.execute(
            """SELECT id FROM public.companies 
               WHERE LOWER(canonical_name) LIKE LOWER(%s) 
               OR LOWER(%s) LIKE LOWER(canonical_name)
               LIMIT 1""",
            (f"%{sponsor_name}%", f"%{sponsor_name}%")
        )
        result = cur.fetchone()
        if result:
            return result[0]
    
    return None

def extract_phase(phase_str):
    """Extract standardized phase from study phase string"""
    if not phase_str:
        return 'N/A'
    
    phase_lower = phase_str.lower()
    if 'phase 1' in phase_lower and 'phase 2' in phase_lower:
        return '1/2'
    elif 'phase 2' in phase_lower and 'phase 3' in phase_lower:
        return '2/3'
    elif 'phase 1' in phase_lower:
        return '1'
    elif 'phase 2' in phase_lower:
        return '2'
    elif 'phase 3' in phase_lower:
        return '3'
    elif 'phase 4' in phase_lower:
        return '4'
    else:
        return 'N/A'

def fetch_recent_studies(days_back=1):
    """Fetch studies updated in the last N days"""
    logger.info(f"Fetching studies updated in last {days_back} days...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    url = f"{CTGOV_API_BASE}/studies"
    params = {
        'format': 'json',
        'fields': 'NCTId,BriefTitle,Phase,OverallStatus,StudyFirstPostDate,PrimaryCompletionDate,LeadSponsorName,Condition',
        'filter.lastUpdatePostDate.min': start_date.strftime('%Y-%m-%d'),
        'pageSize': 1000
    }
    
    studies = []
    page_token = None
    
    while True:
        if page_token:
            params['pageToken'] = page_token
            
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'studies' in data:
                studies.extend(data['studies'])
                logger.info(f"Fetched {len(data['studies'])} studies, total: {len(studies)}")
            
            # Check for next page
            if 'nextPageToken' in data:
                page_token = data['nextPageToken']
            else:
                break
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching studies: {str(e)}")
            break
    
    logger.info(f"Total studies fetched: {len(studies)}")
    return studies

def upsert_trials(studies, conn):
    """Upsert trials into database"""
    logger.info("Upserting trials...")
    
    with conn.cursor() as cur:
        for study in studies:
            protocol_section = study.get('protocolSection', {})
            identification_module = protocol_section.get('identificationModule', {})
            status_module = protocol_section.get('statusModule', {})
            design_module = protocol_section.get('designModule', {})
            sponsor_module = protocol_section.get('sponsorCollaboratorsModule', {})
            conditions_module = protocol_section.get('conditionsModule', {})
            
            nct_id = identification_module.get('nctId')
            title = identification_module.get('briefTitle', '')
            phase = extract_phase(design_module.get('phases', [''])[0] if design_module.get('phases') else '')
            status = status_module.get('overallStatus', '')
            
            # Parse dates
            start_date = None
            if status_module.get('startDateStruct'):
                try:
                    start_date = datetime.strptime(
                        status_module['startDateStruct']['date'], '%Y-%m-%d'
                    ).date()
                except:
                    pass
            
            completion_date = None
            if status_module.get('primaryCompletionDateStruct'):
                try:
                    completion_date = datetime.strptime(
                        status_module['primaryCompletionDateStruct']['date'], '%Y-%m-%d'
                    ).date()
                except:
                    pass
            
            # Match sponsor to company
            sponsor_company_id = None
            if sponsor_module.get('leadSponsor', {}).get('name'):
                sponsor_name = sponsor_module['leadSponsor']['name']
                sponsor_company_id = fuzzy_match_company(sponsor_name, conn)
            
            # Upsert trial
            cur.execute("""
                INSERT INTO public.trials 
                (id, title, phase, status, start_date, primary_completion_date, sponsor_company_id, last_updated, fetched_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    phase = EXCLUDED.phase,
                    status = EXCLUDED.status,
                    start_date = EXCLUDED.start_date,
                    primary_completion_date = EXCLUDED.primary_completion_date,
                    sponsor_company_id = EXCLUDED.sponsor_company_id,
                    last_updated = EXCLUDED.last_updated,
                    fetched_at = EXCLUDED.fetched_at
            """, (
                nct_id, title, phase, status, start_date, completion_date,
                sponsor_company_id, datetime.now(), datetime.now()
            ))
        
        conn.commit()
        logger.info(f"Upserted {len(studies)} trials")

def main():
    """Main ETL function"""
    try:
        conn = get_db_connection()
        logger.info("Connected to database")
        
        # Fetch recent studies (default: 1 day)
        days_back = int(os.getenv('CTGOV_DAYS_BACK', '1'))
        studies = fetch_recent_studies(days_back)
        
        if studies:
            upsert_trials(studies, conn)
            
            # Refresh search view
            with conn.cursor() as cur:
                cur.execute("REFRESH MATERIALIZED VIEW public.search_mv")
                conn.commit()
            
            logger.info("ClinicalTrials.gov ETL completed successfully!")
        else:
            logger.info("No studies to process")
            
    except Exception as e:
        logger.error(f"ETL failed: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
