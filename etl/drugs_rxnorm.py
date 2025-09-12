#!/usr/bin/env python3
"""
RxNorm ETL Script
Enriches drugs table with RxCUI + synonyms from RxNav API
Optimized with batching, parallelization, and caching
"""
import os
import time
import psycopg2
import requests
from psycopg2 import extras
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"

# -----------------------
# DB Helpers
# -----------------------
def get_connection():
    return psycopg2.connect(DATABASE_URL)

def ensure_cache_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS rxnorm_cache (
            product_ndc TEXT PRIMARY KEY,
            rxcui TEXT,
            synonyms TEXT[],
            fetched_at TIMESTAMP DEFAULT now()
        );
        """)
    conn.commit()

# -----------------------
# RxNorm API Helpers
# -----------------------
def fetch_rxcui_batch(ndcs):
    """Fetch RxCUI for a batch of NDCs."""
    ids = "+".join(ndcs)
    url = f"{RXNORM_BASE}/rxcui?idtype=ndc&id={ids}&allsrc=1"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"⚠️ Error fetching batch {ndcs}: {e}")
        return {}

def fetch_synonyms(rxcui):
    """Fetch synonyms for a given RxCUI."""
    url = f"{RXNORM_BASE}/rxcui/{rxcui}/property.json?propName=allName"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        props = data.get("propConceptGroup", {}).get("propConcept", [])
        return [p.get("propValue") for p in props if p.get("propValue")]
    except Exception:
        return []

# -----------------------
# Main Logic
# -----------------------
def enrich_ndcs(ndcs, conn, workers=10, batch_size=20):
    """Enrich a list of NDCs with RxNorm data."""
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        # Batch NDCs
        for i in range(0, len(ndcs), batch_size):
            batch = ndcs[i:i + batch_size]
            futures.append(executor.submit(fetch_rxcui_batch, batch))

        for future in as_completed(futures):
            data = future.result()
            if not data:
                continue
            id_group = data.get("idGroup", {})
            ndc_list = id_group.get("ndcList", {}).get("ndc", [])
            rxnorm_ids = id_group.get("rxnormId", [])
            for ndc, rxcui in zip(ndc_list, rxnorm_ids):
                synonyms = fetch_synonyms(rxcui)
                results.append((ndc, rxcui, synonyms))
    return results

def upsert_cache(results, conn):
    with conn.cursor() as cur:
        extras.execute_values(cur, """
        INSERT INTO rxnorm_cache (product_ndc, rxcui, synonyms)
        VALUES %s
        ON CONFLICT (product_ndc) DO UPDATE SET
            rxcui = EXCLUDED.rxcui,
            synonyms = EXCLUDED.synonyms,
            fetched_at = now();
        """, results)
    conn.commit()

def update_drugs(conn):
    with conn.cursor() as cur:
        cur.execute("""
        UPDATE drugs d
        SET rxcui = c.rxcui,
            drug_synonyms = c.synonyms
        FROM rxnorm_cache c
        WHERE d.product_ndc = c.product_ndc;
        """)
    conn.commit()

def main():
    conn = get_connection()
    ensure_cache_table(conn)

    with conn.cursor() as cur:
        # Get all product_ndc values not yet cached
        cur.execute("""
        SELECT product_ndc FROM drugs
        WHERE product_ndc IS NOT NULL
        AND product_ndc NOT IN (SELECT product_ndc FROM rxnorm_cache);
        """)
        ndcs = [row[0] for row in cur.fetchall()]

    print(f"🔎 Found {len(ndcs)} new NDCs to enrich")

    if ndcs:
        results = enrich_ndcs(ndcs, conn)
        if results:
            upsert_cache(results, conn)
            print(f"✅ Cached {len(results)} new RxNorm mappings")
        else:
            print("⚠️ No new RxNorm results fetched")

    update_drugs(conn)
    print("✅ Drugs table updated with RxNorm data")

    conn.close()

if __name__ == "__main__":
    main()
