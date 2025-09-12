import os
import requests
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

# Load env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

FDA_NDC_API = "https://api.fda.gov/drug/ndc.json"

def fetch_fda_drugs(limit=1000, max_skip=25000):
    """
    Fetch drug data from FDA NDC API with pagination
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

            # Fallback hierarchy for names
            brand_name = (openfda.get("brand_name") or r.get("brand_name") or [None])[0]
            generic_name = (openfda.get("generic_name") or r.get("generic_name") or [None])[0]
            substance_name = (openfda.get("substance_name") or [None])[0]

            preferred_name = (
                (openfda.get("brand_name") or [None])[0]
                or (openfda.get("generic_name") or [None])[0]
                or substance_name
                or r.get("product_ndc")
            )

            drugs.append({
                "preferred_name": preferred_name,
                "generic_name": generic_name,
                "brand_name": brand_name,
                "manufacturer_name": (openfda.get("manufacturer_name") or r.get("labeler_name") or [None])[0],
                "product_ndc": r.get("product_ndc"),
                "package_ndc": (r.get("package_ndc") or [None])[0] if isinstance(r.get("package_ndc"), list) else r.get("package_ndc"),
                "route": (openfda.get("route") or [None])[0],
                "dosage_form": (openfda.get("dosage_form") or [None])[0],
                "pharm_class_epc": (openfda.get("pharm_class_epc") or [None])[0],
                "pharm_class_moa": (openfda.get("pharm_class_moa") or [None])[0],
                "substance_name": substance_name,
                "unii": (openfda.get("unii") or [None])[0],
                "rxcui": (openfda.get("rxcui") or [None])[0],
                "product_type": r.get("product_type"),
                "dea_schedule": r.get("dea_schedule"),
                "marketing_status": r.get("marketing_status"),
                "start_marketing_date": r.get("start_marketing_date"),
                "end_marketing_date": r.get("end_marketing_date"),
                "spl_set_id": r.get("spl_set_id"),
                "spl_id": r.get("spl_id")
            })

        skip += limit

    print(f"✅ Fetched {len(drugs)} drugs from FDA NDC API")
    return drugs


def deduplicate_drugs(drugs):
    """
    Deduplicate by preferred_name + product_ndc
    """
    seen = {}
    for d in drugs:
        key = (d["preferred_name"], d["product_ndc"])
        if key not in seen:
            seen[key] = d
    print(f"✅ {len(seen)} unique drugs after deduplication")
    return list(seen.values())


def upsert_drugs(drugs, conn):
    with conn.cursor() as cur:
        query = """
        INSERT INTO drugs (
            preferred_name, generic_name, brand_name, manufacturer_name,
            product_ndc, package_ndc, route, dosage_form,
            pharm_class_epc, pharm_class_moa, substance_name, unii, rxcui,
            product_type, dea_schedule, marketing_status,
            start_marketing_date, end_marketing_date, spl_set_id, spl_id
        )
        VALUES %s
        ON CONFLICT (product_ndc) DO UPDATE SET
            preferred_name = EXCLUDED.preferred_name,
            generic_name = EXCLUDED.generic_name,
            brand_name = EXCLUDED.brand_name,
            manufacturer_name = EXCLUDED.manufacturer_name,
            route = EXCLUDED.route,
            dosage_form = EXCLUDED.dosage_form,
            pharm_class_epc = EXCLUDED.pharm_class_epc,
            pharm_class_moa = EXCLUDED.pharm_class_moa,
            substance_name = EXCLUDED.substance_name,
            unii = EXCLUDED.unii,
            rxcui = EXCLUDED.rxcui,
            product_type = EXCLUDED.product_type,
            dea_schedule = EXCLUDED.dea_schedule,
            marketing_status = EXCLUDED.marketing_status,
            start_marketing_date = EXCLUDED.start_marketing_date,
            end_marketing_date = EXCLUDED.end_marketing_date,
            spl_set_id = EXCLUDED.spl_set_id,
            spl_id = EXCLUDED.spl_id;
        """
        rows = [
            (
                d.get("preferred_name"),
                d.get("generic_name"),
                d.get("brand_name"),
                d.get("manufacturer_name"),
                d.get("product_ndc"),
                d.get("package_ndc"),
                d.get("route"),
                d.get("dosage_form"),
                d.get("pharm_class_epc"),
                d.get("pharm_class_moa"),
                d.get("substance_name"),
                d.get("unii"),
                d.get("rxcui"),
                d.get("product_type"),
                d.get("dea_schedule"),
                d.get("marketing_status"),
                d.get("start_marketing_date"),
                d.get("end_marketing_date"),
                d.get("spl_set_id"),
                d.get("spl_id")
            )
            for d in drugs
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
