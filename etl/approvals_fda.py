import os
import sys
import requests
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)

DATABASE_URL = os.getenv("DATABASE_URL")

# --- DB connection helper ---
def get_connection():
    return psycopg2.connect(DATABASE_URL)


# --- FDA Approvals fetch ---
def fetch_recent_approvals(days_back=365, max_pages=6, page_size=100):
    cutoff_date = datetime.today() - timedelta(days=days_back)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d")

    url = "https://api.fda.gov/drug/drugsfda.json"

    all_results = []
    for page in range(max_pages):
        params = {
            "search": f"submissions.submission_date:[{cutoff_str}+TO+*]",
            "limit": page_size,
            "skip": page * page_size
        }

        try:
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception as e:
            logging.error(f"Error fetching FDA approvals: {e}")
            break

        if not results:
            logging.info(f"No more results after page {page+1}")
            break

        logging.info(f"Fetched {len(results)} approvals from page {page+1}")
        all_results.extend(results)

    logging.info(f"Total {len(all_results)} FDA approvals fetched")
    return all_results


# --- Transform approvals into DB-ready rows ---
def transform_approvals(results):
    rows = []
    for entry in results:
        appl_no = entry.get("application_number")
        sponsor = entry.get("sponsor_name")
        product = entry.get("products", [{}])[0].get("brand_name")
        submission_date = None

        subs = entry.get("submissions", [])
        if subs:
            submission_date = subs[0].get("submission_date")

        if appl_no and submission_date:
            rows.append((
                appl_no,
                sponsor,
                product,
                submission_date
            ))

    logging.info(f"Prepared {len(rows)} rows for DB upsert")
    return rows


# --- Load into DB ---
def upsert_approvals(rows):
    if not rows:
        logging.warning("No FDA approvals to insert")
        return

    insert_sql = """
        INSERT INTO approvals (application_number, sponsor, product_name, submission_date)
        VALUES %s
        ON CONFLICT (application_number) DO UPDATE
        SET sponsor = EXCLUDED.sponsor,
            product_name = EXCLUDED.product_name,
            submission_date = EXCLUDED.submission_date;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, insert_sql, rows)
        conn.commit()

    logging.info(f"Inserted/updated {len(rows)} FDA approvals into DB")


# --- Main ETL ---
def main():
    logging.info("Connected to database")
    approvals = fetch_recent_approvals(days_back=365)
    rows = transform_approvals(approvals)
    upsert_approvals(rows)
    logging.info("FDA approvals ETL completed successfully!")


if __name__ == "__main__":
    main()
