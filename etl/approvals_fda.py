import os
import requests
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DATABASE_URL = os.getenv("DATABASE_URL")
FDA_API_URL = "https://api.fda.gov/drug/drugsfda.json"
DAYS_BACK = 365


def get_fda_approvals():
    approvals = []
    skip = 0
    limit = 100
    cutoff_date = (datetime.utcnow() - timedelta(days=DAYS_BACK)).date()

    logging.info("Fetching FDA approvals (using submission_status_date)...")

    while True:
        url = f"{FDA_API_URL}?limit={limit}&skip={skip}"
        resp = requests.get(url)

        if resp.status_code != 200:
            logging.error(f"Error fetching FDA approvals: {resp.status_code} {resp.text}")
            break

        data = resp.json()
        results = data.get("results", [])
        if not results:
            break

        logging.info(f"Fetched {len(results)} approvals from page {skip // limit + 1}")

        for r in results:
            application_number = r.get("application_number")
            sponsor = r.get("sponsor_name")
            products = r.get("products", [])
            submissions = r.get("submissions", [])

            for sub in submissions:
                raw_date = sub.get("submission_status_date")
                if not raw_date:
                    continue

                try:
                    submission_date = datetime.strptime(raw_date, "%Y%m%d").date()
                except Exception:
                    continue

                # filter only recent approvals
                if submission_date >= cutoff_date:
                    approvals.append({
                        "application_number": application_number,
                        "sponsor": sponsor,
                        "submission_type": sub.get("submission_type"),
                        "submission_number": sub.get("submission_number"),
                        "submission_status": sub.get("submission_status"),
                        "submission_date": submission_date.isoformat(),
                        "products": [p.get("brand_name") for p in products if "brand_name" in p]
                    })

        skip += limit

    logging.info(f"Total {len(approvals)} FDA approval records after filtering")
    return approvals


def upsert_approvals(approvals):
    if not approvals:
        logging.info("No approvals to process")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    rows = [
        (
            a["application_number"],
            a["sponsor"],
            a["submission_type"],
            a["submission_number"],
            a["submission_status"],
            a["submission_date"],
            a["products"]
        )
        for a in approvals
    ]

    query = """
        INSERT INTO public.approvals
            (application_number, sponsor, submission_type, submission_number, submission_status, submission_date, products)
        VALUES %s
        ON CONFLICT (application_number, submission_number) DO UPDATE
        SET sponsor = EXCLUDED.sponsor,
            submission_type = EXCLUDED.submission_type,
            submission_status = EXCLUDED.submission_status,
            submission_date = EXCLUDED.submission_date,
            products = EXCLUDED.products;
    """

    execute_values(cur, query, rows)
    conn.commit()
    cur.close()
    conn.close()

    logging.info(f"Upserted {len(rows)} approvals into DB")


if __name__ == "__main__":
    logging.info("Connected to database")
    approvals = get_fda_approvals()
    upsert_approvals(approvals)
    logging.info("FDA approvals ETL completed successfully!")
