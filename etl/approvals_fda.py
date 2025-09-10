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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FDA_API_BASE = "https://api.fda.gov"
FDA_URL = f"{FDA_API_BASE}/drug/drugsfda.json"


def _safe_date(s: str):
    """Parse FDA submission_date (YYYYMMDD, YYYYMM, or YYYY)."""
    if not s:
        return None
    for fmt in ("%Y%m%d", "%Y%m", "%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def fetch_approvals(days_back=365, max_pages=6, page_size=100):
    """Fetch FDA approvals and filter locally by submission_date"""
    logger.info(f"Fetching FDA approvals (last {days_back} days)...")
    cutoff_date = datetime.today().date() - timedelta(days=days_back)

    all_results = []
    for page in range(max_pages):
        skip = page * page_size
        params = {"limit": page_size, "skip": skip}
        try:
            resp = requests.get(FDA_URL, params=params, timeout=30)
            if resp.status_code == 404:
                logger.info("No more FDA approvals found")
                break
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                break
            all_results.extend(results)
            logger.info(f"Fetched {len(results)} approvals from page {page+1}")
        except Exception as e:
            logger.error(f"Error fetching FDA approvals: {e}")
            break

    # Filter by cutoff_date
    filtered = []
    for app in all_results:
        submissions = app.get("submissions", [])
        for sub in submissions:
            sub_date = sub.get("submission_date")
            sub_dt = _safe_date(sub_date)
            if sub_dt and sub_dt >= cutoff_date:
                filtered.append(app)
                break  # keep once if any submission is recent

    logger.info(f"Total {len(filtered)} FDA approval records after filtering")
    return filtered


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

                # --- 🔧 TESTING: skip drug match so we actually insert something ---
                drug_id = None  # Replace later with fuzzy_match_drug(drug_name, conn)

                submissions = approval.get("submissions", [])
                for submission in submissions:
                    approval_date = _safe_date(submission.get("submission_date"))
                    if not approval_date:
                        continue

                    docs = submission.get("application_docs", [])
                    for doc in docs:
                        doc_url = doc.get("url", "")
                        doc_type = doc.get("type", "")

                        if "approval" in doc_type.lower():
                            cur.execute("""
                                INSERT INTO public.approvals
                                (agency, approval_date, drug_id, document_url, application_number)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (
                                "FDA",
                                approval_date,
                                drug_id,
                                doc_url,
                                approval.get("application_number", ""),
                            ))
                            processed += 1
                            break  # only one doc per submission

            except Exception as e:
                logger.warning(f"Error processing approval: {e}")
                continue

        conn.commit()
        logger.info(f"Processed {processed} FDA approval records")


def main():
    try:
        conn = get_db_connection()
        logger.info("Connected to database")

        days_back = int(os.getenv("FDA_DAYS_BACK", "365"))
        approvals = fetch_approvals(days_back=days_back)

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
