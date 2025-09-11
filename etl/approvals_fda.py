import os
import requests
import psycopg2
import psycopg2.extras as extras
import json
import logging
from datetime import datetime, timedelta

from psycopg2 import extras
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DATABASE_URL = os.getenv("DATABASE_URL")
FDA_ENDPOINT = "https://api.fda.gov/drug/drugsfda.json"

# -----------------------------
# Fetch FDA approvals
# -----------------------------
def fetch_fda_approvals(limit=100, max_skip=1000):
    approvals = []
    skip = 0

    logging.info("Fetching FDA approvals...")

    while True:
        url = f"{FDA_ENDPOINT}?limit={limit}&skip={skip}"
        logging.info(f"Fetching {url}")
        resp = requests.get(url)

        if resp.status_code != 200:
            logging.error(f"Error fetching FDA approvals: {resp.status_code} {resp.text}")
            break

        data = resp.json()
        results = data.get("results", [])

        if not results:
            break

        approvals.extend(results)
        logging.info(f"Fetched {len(results)} approvals from page skip={skip}")

        skip += limit
        if skip >= max_skip:
            logging.warning("Reached FDA API skip limit (25,000). Stopping pagination.")
            break

    logging.info(f"Total {len(approvals)} FDA approvals fetched")
    return approvals


# -----------------------------
# Upsert approvals into DB
# -----------------------------
def upsert_approvals(approvals, conn):
    """Upsert approvals into database with deduplication"""
    logger.info("Processing FDA approvals...")

    rows = []
    for app in approvals:
        submissions = app.get("submissions", [])
        for sub in submissions:
            rows.append((
                app.get("application_number"),
                app.get("sponsor_name"),
                sub.get("submission_type"),
                sub.get("submission_number"),
                sub.get("submission_status"),
                sub.get("submission_status_date"),
                sub.get("review_priority"),
                sub.get("submission_class_code"),
                sub.get("submission_class_code_description"),
                sub.get("submission_date"),
                app.get("products")
            ))

    # ✅ Deduplicate rows by (application_number, submission_number)
    seen = set()
    deduped = []
    for row in rows:
        key = (row[0], row[3])  # (application_number, submission_number)
        if key not in seen:
            deduped.append(row)
            seen.add(key)

    logger.info(f"Upserting {len(deduped)} unique rows into approvals...")

    query = """
        INSERT INTO approvals (
            application_number, sponsor, submission_type, submission_number,
            submission_status, submission_status_date, review_priority,
            submission_class_code, submission_class_code_description,
            submission_date, products
        )
        VALUES %s
        ON CONFLICT (application_number, submission_number)
        DO UPDATE SET
            sponsor = EXCLUDED.sponsor,
            submission_type = EXCLUDED.submission_type,
            submission_status = EXCLUDED.submission_status,
            submission_status_date = EXCLUDED.submission_status_date,
            products = EXCLUDED.products;
    """

    with conn.cursor() as cur:
        extras.execute_values(cur, query, deduped, page_size=500)
        conn.commit()

    logger.info("FDA approvals upsert completed successfully!")


# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    logging.info("Connected to database")
    approvals = fetch_fda_approvals(limit=100, max_skip=1000)
    upsert_approvals(approvals)
