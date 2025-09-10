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

from db import get_db_connection

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# OpenFDA API base URL
FDA_API_BASE = "https://api.fda.gov"


def fuzzy_match_drug(drug_name, conn):
    """Fuzzy match drug name to existing drug"""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id FROM public.drugs 
               WHERE LOWER(preferred_name) = LOWER(%s) 
               OR LOWER(active_ingredient) = LOWER(%s)""",
            (drug_name, drug_name),
        )
        result = cur.fetchone()
        if result:
            return result[0]

        cur.execute(
            """SELECT id FROM public.drugs 
               WHERE LOWER(preferred_name) LIKE LOWER(%s) 
               OR LOWER(active_ingredient) LIKE LOWER(%s)
               LIMIT 1""",
            (f"%{drug_name}%", f"%{drug_name}%"),
        )
        result = cur.fetchone()
        if result:
            return result[0]

    return None


def fetch_approvals(max_pages=6, page_size=100):
    """Fetch FDA approvals without filtering by date"""
    logger.info("Fetching FDA approvals (bypassing date filter)...")

    url = f"{FDA_API_BASE}/drug/drugsfda.json"
    all_results = []

    for page in range(max_pages):
        params = {"limit": page_size, "skip": page * page_size}
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 404:
                logger.info("No more FDA approvals found")
                break
            resp.raise_for_status()

            data = resp.json()
            results = data.get("results", [])
            if not results:
                break

            logger.info(f"Fetched {len(results)} approvals from page {page+1}")
            all_results.extend(results)

        except Exception as e:
            logger.error(f"Error fetching FDA approvals page {page}: {e}")
            break

    logger.info(f"Total {len(all_results)} FDA approvals fetched (unfiltered)")
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

                drug_name = None
                if brand_names:
                    drug_name = brand_names[0]
                elif generic_names:
                    drug_name = generic_names[0]

                if not drug_name:
                    continue

                drug_id = fuzzy_match_drug(drug_name, conn)
                if not drug_id:
                    continue

                submissions = approval.get("submissions", [])
                for submission in submissions:
                    submission_date = submission.get("submission_date")
                    approval_date = None
                    if submission_date:
                        try:
                            approval_date = datetime.strptime(submission_date, "%Y%m%d").date()
                        except Exception:
                            pass

                    application_docs = submission.get("application_docs", [])
                    for doc in application_docs:
                        doc_url = doc.get("url", "")
                        doc_type = doc.get("type", "")

                        if "approval" in doc_type.lower():
                            cur.execute(
                                """
                                INSERT INTO public.approvals 
                                (agency, approval_date, drug_id, document_url, application_number)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                                """,
                                (
                                    "FDA",
                                    approval_date,
                                    drug_id,
                                    doc_url,
                                    approval.get("application_number", ""),
                                ),
                            )
                            processed += 1
                            break

            except Exception as e:
                logger.warning(f"Error processing approval record: {str(e)}")
                continue

        conn.commit()
        logger.info(f"Processed {processed} FDA approval records")


def main():
    try:
        conn = get_db_connection()
        logger.info("Connected to database")

        approvals = fetch_approvals(max_pages=6, page_size=100)

        if approvals:
            upsert_approvals(approvals, conn)
            logger.info("FDA approvals ETL completed successfully!")
        else:
            logger.info("No approvals to process")

    except Exception as e:
        logger.error(f"FDA Approvals ETL failed: {e}")
        raise
    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    main()
