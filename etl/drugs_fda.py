import os
import requests
import psycopg2
import psycopg2.extras as extras
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")
FDA_NDC_URL = "https://api.fda.gov/drug/ndc.json"

def fetch_fda_drugs(limit=100, max_skip=25000):
    """Fetch drugs from openFDA NDC API"""
    drugs = []
    skip = 0

    while skip < max_skip:
        url = f"{FDA_NDC_URL}?limit={limit}&skip={skip}"
        print(f"Fetching {url} ...")
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"Error {resp.status_code}: {resp.text}")
            break

        data = resp.json()
        results = data.get("results", [])
        if not results:
            break

        for entry in results:
            drugs.append(entry)

        skip += limit

    print(f"✅ Fetched {len(drugs)} drugs from FDA NDC API")
    return drugs


def normalize_drug(entry):
    """Extract fields from FDA NDC entry"""
    brand_name = entry.get("brand_name")
    generic_name = entry.get("generic_name")
    manufacturer = entry.get("labeler_name")
    route = (entry.get("route") or [None])[0]
    dosage_form = entry.get("dosage_form")

    synonyms = set()

    # Collect synonyms from openFDA section
    if "openfda" in entry:
        synonyms.update(entry["openfda"].get("brand_name", []))
        synonyms.update(entry["openfda"].get("generic_name", []))
        synonyms.update(entry["openfda"].get("substance_name", []))

    # Also add product names if available
    if "product_type" in entry:
        synonyms.add(entry["product_type"])

    return {
        "preferred_name": brand_name or generic_name,
        "brand_name": brand_name,
        "generic_name": generic_name,
        "manufacturer": manufacturer,
        "route": route,
        "dosage_form": dosage_form,
        "synonyms": list(synonyms)
    }


def upsert_drugs(drugs, conn):
    """Insert drugs and synonyms into DB"""
    with conn.cursor() as cur:
        rows = []
        synonyms_rows = []

        for d in drugs:
            rows.append((
                d["preferred_name"], d["generic_name"], d["manufacturer"],
                d["route"], d["dosage_form"], datetime.utcnow()
            ))

        query = """
        INSERT INTO drugs (preferred_name, generic_name, manufacturer, route, dosage_form, created_at)
        VALUES %s
        ON CONFLICT (preferred_name) DO UPDATE SET
            generic_name = EXCLUDED.generic_name,
            manufacturer = EXCLUDED.manufacturer,
            route = EXCLUDED.route,
            dosage_form = EXCLUDED.dosage_form;
        """

        extras.execute_values(cur, query, rows)

        # Insert synonyms
        cur.execute("SELECT id, preferred_name FROM drugs;")
        drug_map = {name: did for (did, name) in cur.fetchall()}

        for d in drugs:
            drug_id = drug_map.get(d["preferred_name"])
            if not drug_id:
                continue
            for syn in d["synonyms"]:
                synonyms_rows.append((drug_id, syn, "FDA NDC", datetime.utcnow()))

        if synonyms_rows:
            query_syn = """
            INSERT INTO drug_synonyms (drug_id, synonym, source, created_at)
            VALUES %s
            ON CONFLICT DO NOTHING;
            """
            extras.execute_values(cur, query_syn, synonyms_rows)

    conn.commit()
    print(f"✅ Upserted {len(drugs)} drugs and {len(synonyms_rows)} synonyms")


def main():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        raw_drugs = fetch_fda_drugs(limit=100, max_skip=25000)
        normalized = [normalize_drug(d) for d in raw_drugs]

        # Deduplicate by (brand_name, generic_name)
        seen = set()
        unique_drugs = []
        for d in normalized:
            key = (d["brand_name"], d["generic_name"])
            if key not in seen:
                seen.add(key)
                unique_drugs.append(d)

        print(f"✅ {len(unique_drugs)} unique drugs after deduplication")

        upsert_drugs(unique_drugs, conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
