import os
import requests
import logging
import psycopg2
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FDA_URL = "https://api.fda.gov/drug/drugsfda.json"
PAGE_SIZE = 100
MAX_PAGES = 6

# ---------------------------
# Database connection
# ---------------------------
def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])

# ---------------------------
# Get or create drug
# ---------------------------
def get_or_create_drug(drug_name, conn):
    """Return drug_id if exists, else insert new drug into public.drugs"""
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

        # Insert new drug if not found
        cur.execute(
            """
            INSERT INTO public.drugs (preferred_name, active_ingredient, mechanism, company_id, created_at)
            VALUES (%s, %s, %s, NULL, NOW())
            RETURNING id
            """,
            (drug_name, drug_name, None),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        logger.info(f"Inserted new drug into public.drugs: {drug_name} (id={new_id})")
        return new_id

# ---------------------------
# Fetch FDA approvals
# ---------------------------
def fetch_approvals(days_back=365, max_pages=6):
    approvals = []
    skip = 0
    today = datetime.utcnow().date()
    cutoff = today - timedelta(days=days_back)

    for page in range(max_pages):
        params = {"limit": PAGE_SIZE, "skip": skip}
        try:
            resp = requests.get(FDA_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Error fetching FDA approvals: {e}")
            break

        results = data.get("results", [])
        if not results:
            break

        logger.info(f"Fetched {len(results)} approvals from page {page+1}")

        for r in results:
            submissions = r.get("submissions", [])
            if not submissions:
                continue

            # Take first submission (simplified assumption)
            sub = submissions[0]
            sub_date = sub.get("submission_date")
            if not sub_date:
                continue

            try:
                sub_date_dt = datetime.strptime(sub_date, "%Y%m%d").date()
            except ValueError:
                continue

            # Only take within window
            if sub_date_dt < cutoff:
                continue

            appl_no = r.get("application_number")
            products = r.get("products", [])
            if not products:
                continue

            drug_name = products[0].get("brand_name") or products[0].get("active_ingredients", [{}])[0].get("name")

            if not drug_name:
                continue

            approvals.append({
                "application_number": appl_no,
                "drug_name": drug_name,
                "submission_type": sub.get("submission_type"),
                "submission_status": sub.get("submission_status"),
                "submission_date": sub_date_dt
            })

        skip += PAGE_SIZE

    logger.info(f"Total {len(approvals)} FDA approval records after filtering")
    return approvals

# ---------------------------
# Upsert approvals
# ---------------------------
def upsert_approvals(approvals, conn):
    with conn.cursor() as cur:
        for a in approvals:
            drug_id = get_or_create_drug(a["drug_name"], conn)

            cur.execute(
                """
                INSERT INTO public.approvals (drug_id, source, approval_date, submission_type, status, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (drug_id, source, approval_date)
                DO UPDATE SET status = EXCLUDED.status
                """,
                (
                    drug_id,
                    "FDA",
                    a["submission_date"],
                    a["submission_type"],
                    a["submission_status"],
                ),
            )
    conn.commit()
    logger.info(f"Processed {len(approvals)} FDA approval records")

# ---------------------------
# Main
# ---------------------------
def main():
    conn = get_connection()
    logger.info("Connected to database")

    approvals = fetch_approvals(days_back=365, max_pages=MAX_PAGES)

    if approvals:
        upsert_approvals(approvals, conn)
    else:
        logger.info("No approvals to process")

    conn.close()
    logger.info("FDA approvals ETL completed successfully!")

if __name__ == "__main__":
    main()
