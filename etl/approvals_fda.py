import os
import logging
import psycopg2
import requests
from datetime import datetime, timedelta

# --- Logging setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DATABASE_URL = os.getenv("DATABASE_URL")

def fetch_recent_approvals(days_back=365, max_pages=6, page_size=100):
    """
    Fetch FDA drug approvals from OpenFDA API and filter locally by submission_date.
    """
    cutoff_date = datetime.today() - timedelta(days=days_back)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d")

    url = "https://api.fda.gov/drug/drugsfda.json"

    all_results = []
    for page in range(max_pages):
        params = {"limit": page_size, "skip": page * page_size}
        try:
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception as e:
            logging.error(f"Error fetching FDA approvals: {e}")
            break

        if not results:
            break

        logging.info(f"Fetched {len(results)} approvals from page {page+1}")
        all_results.extend(results)

    logging.info(f"Total {len(all_results)} FDA approvals fetched (unfiltered)")

    # ✅ Local date filter
    filtered = []
    for entry in all_results:
        subs = entry.get("submissions", [])
        if not subs:
            continue
        try:
            submission_date = subs[0].get("submission_date")
            if submission_date and submission_date >= cutoff_str:
                filtered.append(entry)
        except Exception:
            continue

    logging.info(f"Filtered down to {len(filtered)} approvals after {cutoff_str}")

    # 🔎 Show samples for debugging
    for sample in filtered[:5]:
        app_num = sample.get("application_number")
        sponsor = sample.get("sponsor_name")
        subs = sample.get("submissions", [])
        submission_date = subs[0].get("submission_date") if subs else None
        logging.info(f"Sample approval → App#: {app_num}, Sponsor: {sponsor}, Date: {submission_date}")

    return filtered


def upsert_approvals(records):
    """
    Upsert FDA approvals into database.
    """
    if not records:
        logging.warning("No FDA approvals to insert")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    for rec in records:
        app_num = rec.get("application_number")
        sponsor = rec.get("sponsor_name")
        subs = rec.get("submissions", [])
        submission_date = subs[0].get("submission_date") if subs else None

        cur.execute("""
            INSERT INTO approvals (application_number, sponsor_name, submission_date)
            VALUES (%s, %s, %s)
            ON CONFLICT (application_number) DO UPDATE
            SET sponsor_name = EXCLUDED.sponsor_name,
                submission_date = EXCLUDED.submission_date
        """, (app_num, sponsor, submission_date))

    conn.commit()
    cur.close()
    conn.close()

    logging.info(f"Upserted {len(records)} FDA approvals")


def main():
    logging.info("Fetching FDA approvals...")
    approvals = fetch_recent_approvals(days_back=365, max_pages=6, page_size=100)
    upsert_approvals(approvals)
    logging.info("FDA approvals ETL completed successfully!")


if __name__ == "__main__":
    main()
