import os   # ✅ ADD THIS
import requests
import psycopg2
from psycopg2.extras import execute_values
import time

BATCH_SIZE = 20
RXNORM_API = "https://rxnav.nlm.nih.gov/REST/rxcui.json?idtype=ndc&id="

def get_db_connection():
    return psycopg2.connect(dsn=os.environ["DATABASE_URL"])

def fetch_rxcui_batch(ndcs):
    """Fetch RXCUIs for a batch of NDCs"""
    ids = "+".join(ndcs)
    url = RXNORM_API + ids
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        return {}
    data = resp.json()
    result = {}
    for group in data.get("idGroup", {}).get("rxnormIdGroup", []):
        ndc = group.get("ndc", None)
        rxcui = group.get("rxnormId", [None])[0]
        if ndc:
            result[ndc] = rxcui
    return result

def enrich_rxnorm():
    conn = get_db_connection()
    cur = conn.cursor()

    # Get all NDCs without RxCUI
    cur.execute("SELECT product_ndc FROM drugs WHERE rxcui IS NULL")
    all_ndcs = [row[0] for row in cur.fetchall()]
    print(f"Found {len(all_ndcs)} NDCs to enrich")

    resolved = {}
    unresolved = []

    # First pass: bulk resolve
    for i in range(0, len(all_ndcs), BATCH_SIZE):
        batch = all_ndcs[i:i+BATCH_SIZE]
        try:
            result = fetch_rxcui_batch(batch)
            for ndc in batch:
                if ndc in result and result[ndc]:
                    resolved[ndc] = result[ndc]
                else:
                    unresolved.append(ndc)
        except Exception as e:
            print(f"⚠️ Batch failed: {batch[:3]}... {e}")
            unresolved.extend(batch)
        time.sleep(0.2)  # respect API limits

    print(f"✅ First pass: resolved {len(resolved)}, unresolved {len(unresolved)}")

    # Write results
    rows = [(rxcui, ndc) for ndc, rxcui in resolved.items()]
    if rows:
        execute_values(cur,
            "UPDATE drugs SET rxcui = data.rxcui FROM (VALUES %s) AS data(rxcui, product_ndc) WHERE drugs.product_ndc = data.product_ndc",
            rows)
        conn.commit()

    # Second pass: fallback with padding
    still_unresolved = []
    for ndc in unresolved:
        variants = generate_variants(ndc)
        found = None
        for v in variants:
            result = fetch_rxcui_batch([v])
            if v in result and result[v]:
                found = result[v]
                break
            time.sleep(0.3)
        if found:
            resolved[ndc] = found
        else:
            still_unresolved.append(ndc)

    print(f"✅ Second pass resolved: {len(unresolved) - len(still_unresolved)} more")
    print(f"❌ Still unresolved: {len(still_unresolved)}")

    # Write fallback results
    rows = [(rxcui, ndc) for ndc, rxcui in resolved.items()]
    if rows:
        execute_values(cur,
            "UPDATE drugs SET rxcui = data.rxcui FROM (VALUES %s) AS data(rxcui, product_ndc) WHERE drugs.product_ndc = data.product_ndc",
            rows)
        conn.commit()

    cur.close()
    conn.close()


def generate_variants(ndc):
    """Generate padded/unpadded NDC variants"""
    parts = ndc.split("-")
    if len(parts) != 2:
        return [ndc]
    left, right = parts
    variants = [ndc]
    variants.append(f"{left.zfill(5)}-{right.zfill(4)}")  # pad both
    variants.append(f"{left}-{right.zfill(4)}")          # pad right
    variants.append(f"{left.zfill(5)}-{right}")          # pad left
    return list(set(variants))


if __name__ == "__main__":
    enrich_rxnorm()
