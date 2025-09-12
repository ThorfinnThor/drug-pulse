import os
import psycopg2
import requests
import time
import logging

# ---------------------------
# CONFIG
# ---------------------------
RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST/rxcui.json"
BATCH_SIZE = 20   # how many NDCs to query at once
LIMIT = 100       # limit for faster debugging (set to None for full run)
SLEEP = 0.2       # delay between API calls

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ---------------------------
# DB CONNECTION
# ---------------------------
def get_db_connection():
    return psycopg2.connect(dsn=os.environ["DATABASE_URL"])

# ---------------------------
# FETCH DRUGS TO ENRICH
# ---------------------------
def fetch_drugs(conn):
    cur = conn.cursor()
    query = """
        SELECT id, product_ndc
        FROM drugs
        WHERE rxnorm_id IS NULL
    """
    if LIMIT:
        query += f" LIMIT {LIMIT}"
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    return rows

# ---------------------------
# CALL RXNORM API
# ---------------------------
def fetch_rxnorm_id(ndc):
    """Fetch RxCUI from RxNorm API for a single NDC."""
    url = f"{RXNORM_BASE}?idtype=ndc&id={ndc}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rxnorm_id = data.get("idGroup", {}).get("rxnormId", [None])[0]
        return rxnorm_id
    except Exception as e:
        logging.warning(f"Error fetching NDC {ndc}: {e}")
        return None

# ---------------------------
# UPDATE DB
# ---------------------------
def update_rxnorm(conn, updates):
    if not updates:
        return
    cur = conn.cursor()
    for drug_id, rxnorm_id in updates:
        cur.execute(
            "UPDATE drugs SET rxnorm_id = %s WHERE id = %s",
            (rxnorm_id, drug_id),
        )
    conn.commit()
    cur.close()

# ---------------------------
# MAIN ENRICHMENT
# ---------------------------
def enrich_rxnorm():
    conn = get_db_connection()
    drugs = fetch_drugs(conn)
    logging.info(f"Found {len(drugs)} NDCs to enrich (LIMIT={LIMIT})")

    updates = []
    for i, (drug_id, ndc) in enumerate(drugs, 1):
        rxnorm_id = fetch_rxnorm_id(ndc)
        if rxnorm_id:
            updates.append((drug_id, rxnorm_id))
            logging.info(f"✓ {ndc} → RxNorm ID {rxnorm_id}")
        else:
            logging.info(f"✗ {ndc} → No RxNorm ID found")

        # batch update every 50 drugs
        if i % 50 == 0:
            update_rxnorm(conn, updates)
            updates.clear()
            logging.info(f"Committed {i} rows so far...")

        time.sleep(SLEEP)

    # Final commit
    update_rxnorm(conn, updates)
    logging.info("RxNorm enrichment completed")
    conn.close()


if __name__ == "__main__":
    enrich_rxnorm()
