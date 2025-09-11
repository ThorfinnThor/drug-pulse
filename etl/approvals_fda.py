import os
import requests
import psycopg2
from psycopg2 import extras
import logging

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")

DATABASE_URL = os.getenv("DATABASE_URL")
FDA_API_URL = "https://api.fda.gov/drug/drugsfda.json"

def fetch_fda_approvals(limit=100, max_skip=1000):
    approvals = []
    skip = 0

    while skip < max_skip:
        url = f"{FDA_API_URL}?limit={limit}&skip={skip}"
        logging.info(f"Fetching FDA approvals (skip={skip})...")
        r = requests.get(url)

        if r.status_code != 200:
            logging.error(f"Error fetching FDA approvals: {r.status_code} {r.text}")
            break

        data = r.json()
        results = data.get("results", [])
        if not results:
            break

        for record in results:
            application_number = record.get("application_number")
            sponsor = record.get("sponsor_name")
            openfda = record.get("openfda", {})

            # brand & generic names
            brand_name = (
                (openfda.get("brand_name") or [None])[0]
                if openfda.get("brand_name") else None
            )
            generic_name = (
                (openfda.get("generic_name") or [None])[0]
                if openfda.get("generic_name") else None
            )

            # submissions (approval metadata)
            submissions = record.get("submissions", [])
            for sub in submissions:
                submission_type = sub.get("submission_type")
                submission_number = sub.get("submission_number")
                submission_status = sub.get("submission_status")
                submission_status_date = sub.get("submission_status_date")
                review_priority = sub.get("review_priority")
                submission_class_code = sub.get("submission_class_code")
                submission_class_code_description = sub.get("submission_class_code_description")

                approval_date = submission_status_date
                agency = "FDA"

                # document url
                document_url = None
                if "application_docs" in sub:
                    docs = sub["application_docs"]
                    if docs:
                        document_url = docs[0].get("url")

                # products
               # products
products = record.get("products", [])
for prod in products:
    route = prod.get("route")
    dosage_form = prod.get("dosage_form")

    approvals.append((
        application_number, sponsor, brand_name, generic_name,
        submission_type, submission_number, submission_status,
        submission_status_date, review_priority,
        submission_class_code, submission_class_code_description,
        approval_date, agency, document_url, route, dosage_form,
        json.dumps(products)  # 🔑 FIXED
    ))


        skip += limit

    logging.info(f"Total {len(approvals)} FDA approvals fetched")
    return approvals

def upsert_approvals(approvals, conn):
    with conn.cursor() as cur:
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

        # deduplicate in-memory first
        seen = set()
        unique_rows = []
        for row in approvals:
            key = (row[0], row[5])  # (application_number, submission_number)
            if key not in seen:
                seen.add(key)
                unique_rows.append(row)

        logging.info(f"Upserting {len(unique_rows)} unique approvals into DB...")

        extras.execute_values(cur, query, unique_rows)
    conn.commit()

def main():
    conn = psycopg2.connect(DATABASE_URL)
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
