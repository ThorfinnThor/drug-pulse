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
                "proprietary_name": (openfda.get("brand_name") or [None])[0],
                "generic_name": (openfda.get("generic_name") or [None])[0],
                "manufacturer_name": (openfda.get("manufacturer_name") or [None])[0],

                # Arrays
                "substance_name": openfda.get("substance_name", []),
                "route": openfda.get("route", []),
                "dosage_form": (openfda.get("dosage_form") or [None])[0],
                "pharm_class_epc": openfda.get("pharm_class_epc", []),
                "pharm_class_moa": openfda.get("pharm_class_moa", []),

                "unii": openfda.get("unii", []),
                "rxcui": openfda.get("rxcui", []),

                # Labels / metadata
                "spl_set_id": r.get("spl_set_id"),
                "spl_id": r.get("spl_id"),
                "marketing_status": r.get("marketing_status"),
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
            product_ndc, proprietary_name, generic_name, manufacturer_name,
            substance_name, route, dosage_form,
            pharm_class_epc, pharm_class_moa, unii, rxcui,
            spl_set_id, spl_id, marketing_status
        )
        VALUES %s
        ON CONFLICT (product_ndc) DO UPDATE SET
            proprietary_name = EXCLUDED.proprietary_name,
            generic_name = EXCLUDED.generic_name,
            manufacturer_name = EXCLUDED.manufacturer_name,
            substance_name = EXCLUDED.substance_name,
            route = EXCLUDED.route,
            dosage_form = EXCLUDED.dosage_form,
            pharm_class_epc = EXCLUDED.pharm_class_epc,
            pharm_class_moa = EXCLUDED.pharm_class_moa,
            unii = EXCLUDED.unii,
            rxcui = EXCLUDED.rxcui,
            spl_set_id = EXCLUDED.spl_set_id,
            spl_id = EXCLUDED.spl_id,
            marketing_status = EXCLUDED.marketing_status;
        """
        rows = [
            (
                d.get("product_ndc"),
                d.get("proprietary_name"),
                d.get("generic_name"),
                d.get("manufacturer_name"),
                d.get("substance_name"),
                d.get("route"),
                d.get("dosage_form"),
                d.get("pharm_class_epc"),
                d.get("pharm_class_moa"),
                d.get("unii"),
                d.get("rxcui"),
                d.get("spl_set_id"),
                d.get("spl_id"),
                d.get("marketing_status"),
            )
            for d in drugs
        ]
        extras.execute_values(cur, query, rows, page_size=1000)
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
