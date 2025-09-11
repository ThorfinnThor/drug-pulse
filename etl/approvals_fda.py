import os
import requests
import psycopg2
import psycopg2.extras as extras
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

FDA_API_URL = "https://api.fda.gov/drug/drugsfda.json"
BATCH_SIZE = 100
MAX_SKIP = 1000  # FDA API limit

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def fetch_fda_approvals(limit=100, max_skip=MAX_SKIP):
    approvals = []
    skip = 0

    while skip <= max_skip:
        params = {"limit": limit, "skip": skip}
        logging.info(f"Fetching FDA approvals with skip={skip}...")

        resp = requests.get(FDA_API_URL, params=params)
        if resp.status_code != 200:
            logging.error(f"Error fetching FDA approvals: {resp.status_code} {resp.text}")
            break

        data = resp.json()
        results = data.get("results", [])
        if not results:
            break

        for record in results:
            application_number = record.get("application_number")
            sponsor = record.get("sponsor_name")
            agency = record.get("agency", "FDA")

            submissions = record.get("submissions", [])
            products = record.get("products", [])

            for sub in submissions:
                submission_type = sub.get("submission_type")
                submission_number = sub.get("submission_number")
                submission_status = sub.get("submission_status")
                submission_status_date = sub.get("submission_status_date")
                review_priority = sub.get("review_priority")
                submission_class_code = sub.get("submission_class_code")
                submission_class_code_description = sub.get("submission_class_code_description")
                approval_date = None
                if submission_status_date:
                    try:
                        approval_date = datetime.strptime(submission_status_date, "%Y%m%d").date()
                    except Exception:
                        pass
                document_url = None
                docs = sub.get("application_docs", [])
                if docs:
                    document_url = docs[0].get("url")

                # product details
                for prod in products:
                    brand_name = (
                        prod.get("brand_name")
                        or record.get("openfda", {}).get("brand_name", [None])[0]
                    )
                    generic_name = (
                        prod.get("generic_name")
                        or record.get("openfda", {}).get("generic_name", [None])[0]
                    )
                    route = prod.get("route")
                    dosage_form = prod.get("dosage_form")

                    approvals.append((
                        application_number, sponsor, brand_name, generic_name,
                        submission_type, submission_number, submission_status,
                        submission_status_date, review_priority,
                        submission_class_code, submission_class_code_description,
                        approval_date, agency, document_url, route, dosage_form,
                        json.dumps(products)  # ✅ convert dict/list → JSON string
                    ))

        skip += limit
        if skip > max_skip:
            logging.warning("Reached FDA API skip limit (25,000). Stopping pagination.")
            break

    logging.info(f"Total {len(approvals)} FDA approvals fetched")
    return approvals

def upsert_approvals(approvals, conn):
    if not approvals:
        logging.info("No approvals to insert")
        return

    # deduplicate (application_number + submission_number)
    seen = set()
    unique_rows = []
    for row in approvals:
        key = (row[0], row[5])  # application_number + submission_number
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)

    logging.info(f"Upserting {len(unique_rows)} unique approvals into DB...")

    query = """
        INSERT INTO approvals (
            application_number, sponsor, brand_name, generic_name,
            submission_type, submission_number, submission_status,
            submission_status_date, review_priority,
            submission_class_code, submission_class_code_description,
            approval_date, agency, document_url, route, dosage_form, products
        )
        VALUES %s
        ON CONFLICT (application_number, submission_number)
        DO UPDATE SET
            sponsor = EXCLUDED.sponsor,
            brand_name = EXCLUDED.brand_name,
            generic_name = EXCLUDED.generic_name,
            submission_status = EXCLUDED.submission_status,
            submission_status_date = EXCLUDED.submission_status_date,
            review_priority = EXCLUDED.review_priority,
            submission_class_code = EXCLUDED.submission_class_code,
            submission_class_code_description = EXCLUDED.submission_class_code_description,
            approval_date = EXCLUDED.approval_date,
            agency = EXCLUDED.agency,
            document_url = EXCLUDED.document_url,
            route = EXCLUDED.route,
            dosage_form = EXCLUDED.dosage_form,
            products = EXCLUDED.products;
    """

    with conn.cursor() as cur:
        extras.execute_values(cur, query, unique_rows, page_size=500)
    conn.commit()

def main():
    conn = get_db_connection()
    try:
        approvals = fetch_fda_approvals()
        upsert_approvals(approvals, conn)
        logging.info("FDA approvals ETL completed successfully!")
    except Exception as e:
        logging.error(f"FDA approvals ETL failed: {e}", exc_info=True)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
