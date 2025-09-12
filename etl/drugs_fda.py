import os
import requests
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

FDA_NDC_API = "https://api.fda.gov/drug/ndc.json"

def fetch_fda_drugs(limit=1000, max_skip=25000):
    """
    Fetch drug data from the FDA NDC API with pagination up to skip limit.
    """
    drugs = []
    skip = 0
    while skip < max_skip:
        url = f"{FDA_NDC_API}?limit={limit}&skip={skip}"
        print(f"Fetching {url} ...")
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"Error fetching data: {resp.status_code} {resp.text}")
            break

        data = resp.json()
        results = data.get("results", [])
        if not results:
            break

        for r in results:
            openfda = r.get("openfda", {})

            drugs.append({
                "product_ndc": r.get("product_ndc"),
                "generic_name": (openfda.get("generic_name") or [None])[0],
                "manufacturer_name": (openfda.get("manufacturer_name") or [None])[0],
                "route": (openfda.get("route") or [None])[0],
                "dosage_form": (openfda.get("dosage_form") or [None])[0],
                "pharm_class": (openfda.get("pharm_class_epc") or [None])[0],
                "substance_name": (openfda.get("substance_name") or [None])[0],
                "unii": (openfda.get("unii") or [None])[0],
                "rxcui": (openfda.get("rxcui") or [None])[0],
                "marketing_status": r.get("marketing_status"),
                "start_marketing_date": r.get("start_marketing_date"),
                "end_marketing_date": r.get("end_marketing_date"),
                "dea_schedule": r.get("dea_schedule"),
                "product_type": r.get("product_type"),
            })

        skip += limit

    print(f"✅ Fetched {len(drugs)} drugs from FDA NDC API")
    return drugs

def deduplicate_drugs(drugs):
    """
    Deduplicate drugs by product_ndc.
    """
    seen = {}
    for d in drugs:
        key = d["product_ndc"]
        if key and key not in seen:
            seen[key] = d
    print(f"✅ {len(seen)} unique drugs after deduplication")
    return list(seen.values())

def upsert_drugs(drugs, conn):
    with conn.cursor() as cur:
        query = """
        INSERT INTO drugs (
            product_ndc, generic_name, manufacturer_name, route, dosage_form,
            pharm_class, substance_name, unii, rxcui, marketing_status,
            start_marketing_date, end_marketing_date, dea_schedule, product_type
        )
        VALUES %s
        ON CONFLICT (product_ndc) DO UPDATE SET
            generic_name = EXCLUDED.generic_name,
            manufacturer_name = EXCLUDED.manufacturer_name,
            route = EXCLUDED.route,
            dosage_form = EXCLUDED.dosage_form,
            pharm_class = EXCLUDED.pharm_class,
            substance_name = EXCLUDED.substance_name,
            unii = EXCLUDED.unii,
            rxcui = EXCLUDED.rxcui,
            marketing_status = EXCLUDED.marketing_status,
            start_marketing_date = EXCLUDED.start_marketing_date,
            end_marketing_date = EXCLUDED.end_marketing_date,
            dea_schedule = EXCLUDED.dea_schedule,
            product_type = EXCLUDED.product_type;
        """
        rows = [
            (
                d.get("product_ndc"),
                d.get("generic_name"),
                d.get("manufacturer_name"),
                d.get("route"),
                d.get("dosage_form"),
                d.get("pharm_class"),
                d.get("substance_name"),
                d.get("unii"),
                d.get("rxcui"),
                d.get("marketing_status"),
                d.get("start_marketing_date"),
                d.get("end_marketing_date"),
                d.get("dea_schedule"),
                d.get("product_type"),
            )
            for d in drugs if d.get("product_ndc")  # only insert if product_ndc is present
        ]
        extras.execute_values(cur, query, rows, page_size=500)
    conn.commit()


def main():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        drugs = fetch_fda_drugs()
        unique_drugs = deduplicate_drugs(drugs)
        upsert_drugs(unique_drugs, conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
