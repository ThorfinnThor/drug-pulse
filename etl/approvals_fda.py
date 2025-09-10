#!/usr/bin/env python3
"""
FDA Approvals ETL Script
Fetches FDA drug approvals from openFDA API and upserts into database
"""
import os
import requests
import psycopg2
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta

from db import get_db_connection 

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# OpenFDA API base URL
FDA_API_BASE = "https://api.fda.gov"


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


def fetch_recent_approvals(days_back=365, max_pages=5):
    """Fetch FDA approvals and filter locally by submission_date"""
    logger.info(f"Fetching FDA approvals (last {days_back} days)...")

    url = f"{FDA_API_BASE}/drug/drugsfda.json"
    cutoff_date = datetime.today() - timedelta(days=days_back)

    all_filtered = []
    page_size = 100

    for page in range(max_pages):  # fetch multiple pages
        params = {"limit": page_size, "skip": page * page_size}
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 404:
                logger.info("No FDA approvals found")
                break
            resp.raise_for_status()

            data = resp.json()
            approvals = data.get("results", [])
            if not approvals:
                break  # no more data

            for app in approvals:
                submissions = app.get("submissions", [])
                for sub in submissions:
                    sub_date = sub.get("submission_date")
                    if not sub_date:
                        continue
                    try:
                        # pad if date is shorter than 8 chars
                        sub_date = sub_date.ljust(8, "0")
                        sub_dt = datetime.strptime(sub_date, "%Y%m%d").date()
                    except ValueError:
                        continue

                    if sub_dt >= cutoff_date.date():
                        all_filtered.append(app)
                        break  # only include once per application

        except Exception as e:
            logger.error(f"Error fetching FDA approvals: {e}")
            break

    logger.info(f"Fetched {len(all_filtered)} FDA approval records after filtering")
    return all_filtered


def upsert_approvals(approvals, conn):
    """Upsert approvals into database"""
    logger.info("Processing FDA approvals...")
    
    with conn.cursor() as cur:
        processed = 0
        sample_logged = 0  # track how many we log visibly

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
                        # pad date if shorter than 8 chars
                        submission_date = submission_date.ljust(8, "0")
                        approval_date = datetime.strptime(submission_date, '%Y%m%d').date()
                    except Exception:
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

                            # log the first 5 we insert
                            if sample_logged < 5:
                                logger.info(f"Inserted: {drug_name} on {approval_date}")
                                sample_logged += 1

                            break  # only log one doc per submission
                
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
        logger.error(f"ETL failed: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
