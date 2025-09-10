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
import time

from db import get_db_connection 

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# OpenFDA API base URL
FDA_API_BASE = "https://api.fda.gov"
FDA_URL = f"{FDA_API_BASE}/drug/drugsfda.json"


def fuzzy_match_drug(drug_name, conn):
    """Fuzzy match drug name to existing drug"""
    with conn.cursor() as cur:
        # Exact match
        cur.execute(
            """SELECT id FROM public.drugs 
               WHERE LOWER(preferred_name) = LOWER(%s) 
               OR LOWER(active_ingredient) = LOWER(%s)""",
            (drug_name, drug_name)
        )
        result = cur.fetchone()
        if result:
            return result[0]

        # Partial match
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
    """Fetch FDA approvals with pagination and local filtering"""
    logger.info(f"Fetching FDA approvals (last {days_back} days)...")

    cutoff_date = datetime.today() - timedelta(days=days_back)
    all_results = []

    for page in range(max_pages):
        params = {"limit": 100, "skip": page * 100}
        try:
            resp = requests.get(FDA_URL, params=params, timeout=30)
            if resp.status_code == 404:
                logger.info("No FDA approvals found on this page")
                break
            resp.raise_for_status()

            data = resp.json()
            results = data.get("results", [])
            if not results:
                break

            for app in results:
                submissions = app.get("submissions", [])
                for sub in submissions:
                    sub_date = sub.get("submission_date")
                    if not sub_date:
                        continue
                    try:
                        sub_dt = datetime.strptime(sub_date, "%Y%m%d").date()
                    except ValueError:
                        continue

                    if sub_dt >= cutoff_date.date():
                        all_results.append(app)
                        break  # include approval once if any submission is recent

            logger.info(f"Fetched {len(results)} approvals from page {page+1}")

            # Respect API rate limits
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error fetching FDA approvals: {e}")
            break

    logger.info(f"Total {len(all_results)} FDA approval records after filtering")
    return all_results


def upsert_approvals(approvals, conn):
    """Upsert approvals into database"""
    logger.info("Processing FDA approvals...")

    with conn.cursor() as cur:
        processed = 0

        for approval in approvals:
            try:
                openfda = approval.get("openfda", {})
                brand_names = openfda.get("brand_name", [])
                generic_names = openfda.get("generic_name", [])

                drug_name = brand_names[0] if brand_names else (generic_names[0] if generic_names else None)
                if not drug_name:
                    continue

                drug_id = fuzzy_match_drug(drug_name, conn)
                if not drug_id:
                    continue

                submissions = approval.get("submissions", [])
                for submission in submissions:
                    submission_date = submission.get("submission_date")
                    if not submission_date:
                        continue

                    try:
                        approval_date = datetime.strptime(submission_date, "%Y%m%d").date()
                    except Exception:
                        continue

                    application_docs = submission.get("application_docs", [])
                    for doc in application_docs:
                        doc_url = doc.get("url", "")
                        doc_type = doc.get("type", "")

                        if "approval" in doc_type.lower():
                            cur.execute("""
                                INSERT INTO public.approvals 
                                (agency, approval_date, drug_id, document_url, application_number)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (
                                "FDA", approval_date, drug_id, doc_url,
                                approval.get("application_number", "")
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

        days_back = int(os.getenv("FDA_DAYS_BACK", "30"))
        approvals = fetch_recent_approvals(days_back=days_back, max_pages=6)

        if approvals:
            upsert_approvals(approvals, conn)
            logger.info("FDA approvals ETL completed successfully!")
        else:
            logger.info("No approvals to process")

    except Exception as e:
        logger.error(f"ETL failed: {e}")
        raise
    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    main()
