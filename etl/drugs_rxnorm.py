import os
import requests
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
import time

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"

def fetch_rxcui_by_ndc(ndc: str):
    """Fetch RxCUI for a given NDC code"""
    url = f"{RXNORM_BASE}/rxcui.json?idtype=ndc&id={ndc}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None
    data = resp.json()
    return data.get("idGroup", {}).get("rxnormId", [None])[0]

def fetch_rxnorm_properties(rxcui: str):
    """Fetch drug properties (name, synonyms) for RxCUI"""
    url = f"{RXNORM_BASE}/rxcui/{rxcui}/allProperties.json?prop=names"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None, []
    data = resp.json()
    props = data.get("propConceptGroup", {}).get("propConcept", [])
    names = [p["propValue"] for p in props if "propValue" in p]

    # Best guess: first is preferred name
    preferred_name = names[0] if names else None
    return preferred_name, names

def upsert_rxnorm(conn, rows):
    """Upsert RxNorm data into drugs table and synonyms table"""
    with conn.cursor() as cur:
        # Update drugs table
        query = """
        UPDATE drugs d
        SET rxcui = data.rxcui,
            generic_name = COALESCE(data.generic_name, d.generic_name),
            brand_name = COALESCE(data.brand_name, d.brand_name)
        FROM (VALUES %s) AS data(product_ndc, rxcui, generic_name, brand_name)
        WHERE d.product_ndc = data.product_ndc;
        """
        extras.execute_values(
            cur, query, rows, template=None, page_size=500
        )
    conn.commit()

def insert_synonyms(conn, synonym_rows):
    """Insert synonyms into drug_synonyms table (create if not exists)"""
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS drug_synonyms (
            id SERIAL PRIMARY KEY,
            drug_id INT REFERENCES drugs(id) ON DELETE CASCADE,
            synonym TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
        query = """
        INSERT INTO drug_synonyms (drug_id, synonym)
        VALUES %s
        ON CONFLICT DO NOTHING;
        """
        extras.execute_values(cur, query, synonym_rows, page_size=500)
    conn.commit()

def main():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, product_ndc FROM drugs WHERE product_ndc IS NOT NULL;")
        ndc_rows = cur.fetchall()

        update_rows = []
        synonym_rows = []

        for drug_id, ndc in ndc_rows:
            if not ndc:
                continue
            rxcui = fetch_rxcui_by_ndc(ndc)
            if not rxcui:
                continue

            preferred_name, synonyms = fetch_rxnorm_properties(rxcui)
            if not preferred_name:
                continue

            # Heuristic: if multiple names, pick the shortest as generic_name
            generic_name = min(synonyms, key=len) if synonyms else None
            brand_name = preferred_name if preferred_name != generic_name else None

            update_rows.append((ndc, rxcui, generic_name, brand_name))

            for syn in synonyms:
                synonym_rows.append((drug_id, syn))

            time.sleep(0.2)  # avoid hammering API

        if update_rows:
            upsert_rxnorm(conn, update_rows)

        if synonym_rows:
            insert_synonyms(conn, synonym_rows)

        print(f"✅ Updated {len(update_rows)} drugs with RxNorm data")
        print(f"✅ Inserted {len(synonym_rows)} synonyms")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
