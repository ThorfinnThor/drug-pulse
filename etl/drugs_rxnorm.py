import os
import time
import requests
import psycopg2
from psycopg2 import extras
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"


# --------------------------
# Fetch functions
# --------------------------

def fetch_synonyms(rxcui):
    """Fetch synonyms for a given RxCUI."""
    if not rxcui:
        return []
    url = f"{RXNORM_BASE}/rxcui/{rxcui}/allProperties.json?prop=all"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        props = data.get("propConceptGroup", {}).get("propConcept", [])
        return list({p.get("propValue") for p in props if "propValue" in p})
    except Exception as e:
        print(f"⚠️ Error fetching synonyms for {rxcui}: {e}")
        return []


def fetch_rxcui_for_ndc(ndc):
    """Fetch RxCUI + synonyms for a single NDC."""
    url = f"{RXNORM_BASE}/rxcui?idtype=ndc&id={ndc}&allsrc=1"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rxcui = data.get("idGroup", {}).get("rxnormId", [None])[0]
        synonyms = fetch_synonyms(rxcui) if rxcui else []
        return (ndc, rxcui, synonyms)
    except Exception as e:
        print(f"⚠️ Error fetching NDC {ndc}: {e}")
        return (ndc, None, [])


# --------------------------
# Enrichment
# --------------------------

def enrich_ndcs(ndcs, workers=20):
    """Enrich a list of NDCs with RxNorm data in parallel (per-NDC)."""
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_rxcui_for_ndc, ndc): ndc for ndc in ndcs}
        for future in as_completed(futures):
            results.append(future.result())
    return results


# --------------------------
# Database operations
# --------------------------

def get_ndcs_to_enrich(conn):
    """Get NDCs from the database that do not yet have an RxCUI."""
    with conn.cursor() as cur:
        cur.execute("SELECT product_ndc FROM drugs WHERE rxcui IS NULL")
        rows = cur.fetchall()
    return [r[0] for r in rows if r[0]]


def upsert_rxnorm_data(results, conn):
    """Upsert RxNorm data back into the drugs table."""
    with conn.cursor() as cur:
        query = """
        UPDATE drugs
        SET rxcui = data.rxcui,
            synonyms = data.synonyms
        FROM (VALUES %s) AS data(ndc, rxcui, synonyms)
        WHERE drugs.product_ndc = data.ndc;
        """
        rows = [
            (ndc, rxcui, synonyms if synonyms else None)
            for ndc, rxcui, synonyms in results
        ]
        extras.execute_values(cur, query, rows, page_size=500)
    conn.commit()


# --------------------------
# Main
# --------------------------

def main():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        ndcs = get_ndcs_to_enrich(conn)
        print(f"🔍 Found {len(ndcs)} new NDCs to enrich")

        results = enrich_ndcs(ndcs, workers=20)

        upsert_rxnorm_data(results, conn)
        print(f"✅ Enriched {len(results)} NDCs with RxNorm data")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
