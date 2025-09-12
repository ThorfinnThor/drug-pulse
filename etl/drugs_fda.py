import os
import requests
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

FDA_NDC_API = "https://api.fda.gov/drug/ndc.json"

def fetch_fda_drugs(limit=1000, max_skip=1000):
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
                "preferred_name": (openfda.get("brand_name") or openfda.get("generic_name") or ["UNKNOWN"])[0],
                "generic_name": (openfda.get("generic_name") or [None])[0],
                "brand_name": (openfda.get("brand_name") or [None])[0],
                "manufacturer_name": (openfda.get("manufacturer_name") or [None])[0],
                "product_ndc": r.get("product_ndc"),
                "package_ndc": (r.get("package_ndc") or [None])[0] if isinstance(r.get("package_ndc"), list) else r.get("package_ndc"),
                "route": (openfda.get("route") or [None])[0],
                "dosage_form": (openfda.get("dosage_form") or [None])[0],
                "pharm_class": (openfda.get("pharm_class_epc") or [None])[0],
                "product_type": r.get("product_type"),
                "dea_schedule": r.get("dea_schedule"),
                "substance_name": (openfda.get("substance_name") or [None])[0],
                "unii": (openfda.get("unii") or [None])[0],
                "rxcui": (openfda.get("rxcui") or [None])[0],
                "marketing_status": r.get("marketing_status"),
                "start_marketing_date": r.get("start_marketing_date"),
                "end_marketing_date": r.get("end_marketing_date")
            })

        skip += limit

    print(f"✅ Fetched {len(drugs)} drugs from FDA NDC API")
    return drugs

def deduplicate_drugs(drugs):
    """
    Deduplicate drugs by preferred_name + product_ndc.
    """
    seen = {}
    for d in drugs:
        key = (d["preferred_name"], d["product_ndc"])
        if key not in seen:
            seen[key] = d
    print(f"✅ {len(seen)} unique drugs after deduplication")
    return list(seen.values())

def upsert_drugs(drugs, conn):
    """
    Upsert drug records into the drugs table.
    """
    with conn.cursor() as cur:
        query = """
            INSERT INTO drugs (
                preferred_name, generic_name, brand_name, manufacturer_name,
                product_ndc, package_ndc, route, dosage_form,
                pharm_class, product_type, dea_schedule,
                substance_name, unii, rxcui,
                marketing_status, start_marketing_date, end_marketing_date
            )
            VALUES %s
            ON CONFLICT (preferred_name)
            DO UPDATE SET
                generic_name = EXCLUDED.generic_name,
                brand_name = EXCLUDED.brand_name,
                manufacturer_name = EXCLUDED.manufacturer_name,
                route = EXCLUDED.route,
                dosage_form = EXCLUDED.dosage_form,
                pharm_class = EXCLUDED.pharm_class,
                product_type = EXCLUDED.product_type,
                dea_schedule = EXCLUDED.dea_schedule,
                marketing_status = EXCLUDED.marketing_status,
                start_marketing_date = EXCLUDED.start_marketing_date,
                end_marketing_date = EXCLUDED.end_marketing_date;
        """
        rows = [
            (
                d["preferred_name"], d["generic_name"], d["brand_name"], d["manufacturer_name"],
                d["product_ndc"], d["package_ndc"], d["route"], d["dosage_form"],
                d["pharm_class"], d["product_type"], d["dea_schedule"],
                d["substance_name"], d["unii"], d["rxcui"],
                d["marketing_status"], d["start_marketing_date"], d["end_marketing_date"]
            )
            for d in drugs
        ]

        extras.execute_values(cur, query, rows)
        conn.commit()
    print(f"✅ Upserted {len(drugs)} drugs into DB")

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
