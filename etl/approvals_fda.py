import os
import requests
import psycopg2
import psycopg2.extras as extras
import json
import logging
from datetime import datetime, timedelta

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
def upsert_approvals(approvals):
    if not approvals:
        logging.info("No approvals to process")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    rows = []
    for approval in approvals:
        submissions = approval.get("submissions", [])
        products = approval.get("products", [])

        for sub in submissions:
            rows.append((
                approval.get("application_number"),
                approval.get("sponsor_name"),
                sub.get("submission_type"),
                sub.get("submission_number"),
                sub.get("submission_status"),
                sub.get("submission_status_date"),
                sub.get("review_priority"),
                sub.get("submission_class_code"),
                sub.get("submission_class_code_description"),
                sub.get("submission_date"),
                json.dumps(products)  # ✅ ensure JSON not text[]
            ))

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
            review_priority = EXCLUDED.review_priority,
            submission_class_code = EXCLUDED.submission_class_code,
            submission_class_code_description = EXCLUDED.submission_class_code_description,
            submission_date = EXCLUDED.submission_date,
            products = EXCLUDED.products;
    """

    logging.info(f"Upserting {len(rows)} rows into approvals...")
    extras.execute_values(cur, query, rows)
    conn.commit()

    cur.close()
    conn.close()
    logging.info("FDA approvals upsert completed successfully!")


# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    logging.info("Connected to database")
    approvals = fetch_fda_approvals(limit=100, max_skip=25000)
    upsert_approvals(approvals)
