import os
import time
import json
import logging
from typing import Dict, List, Optional, Set, Tuple

import psycopg2
from psycopg2 import extras
import requests

# -------------------------
# Config (override with env)
# -------------------------
MAX_ROWS = int(os.getenv("RXNORM_ENRICH_LIMIT", "500"))          # how many drug rows to enrich per run
HTTP_TIMEOUT = float(os.getenv("RXNORM_HTTP_TIMEOUT", "12"))     # seconds
RETRY_MAX = int(os.getenv("RXNORM_RETRY_MAX", "3"))
RETRY_BACKOFF = float(os.getenv("RXNORM_RETRY_BACKOFF", "0.8"))  # seconds
SLEEP_BETWEEN_CALLS = float(os.getenv("RXNORM_SLEEP", "0.10"))   # seconds between HTTP calls

DATABASE_URL = os.getenv("DATABASE_URL")

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"

# Which RxNorm term types we'll treat as synonyms
SYN_TTYS: Set[str] = {"BN", "SBD", "SCD", "IN", "PIN", "MIN"}

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL)

def fetch_columns(conn, table: str) -> Set[str]:
    """Return set of column names present in the table (lowercase)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
        """, (table,))
        return {r[0].lower() for r in cur.fetchall()}

def select_rows_to_enrich(conn, limit: int) -> List[Tuple[int, str]]:
    """
    Pick rows that have rxnorm_id but are missing ingredient OR tradename OR rxnorm_synonyms.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, rxnorm_id
            FROM drugs
            WHERE rxnorm_id IS NOT NULL
              AND (ingredient IS NULL OR tradename IS NULL OR rxnorm_synonyms IS NULL)
            ORDER BY id
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()

def http_get_json(url: str) -> Optional[dict]:
    """
    GET -> JSON with simple retry/backoff.
    """
    for attempt in range(1, RETRY_MAX + 1):
        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": "drug-pulse/1.0"})
            if resp.status_code == 200:
                return resp.json()
            else:
                logging.warning("RxNav non-200 (%s) for %s", resp.status_code, url)
        except requests.RequestException as e:
            logging.warning("RxNav request failed (%s) for %s", e, url)
        if attempt < RETRY_MAX:
            time.sleep(RETRY_BACKOFF * attempt)
    return None

def parse_related_for_enrichment(data: dict) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    From /rxcui/{id}/allRelated.json extract:
      - ingredient: first IN (else PIN)
      - tradename: first BN
      - synonyms: union of names across SYN_TTYS
    """
    ingredient: Optional[str] = None
    tradename: Optional[str] = None
    synonyms: Set[str] = set()

    try:
        groups = data.get("allRelatedGroup", {}).get("conceptGroup", [])
        for grp in groups:
            tty = (grp.get("tty") or "").upper().strip()
            props = grp.get("conceptProperties") or []
            if not props:
                continue

            # Pull ingredient (prefer IN, else PIN)
            if tty == "IN" and not ingredient:
                ingredient = props[0].get("name")
            if tty == "PIN" and not ingredient:  # precise ingredient fallback
                ingredient = props[0].get("name")

            # First BN becomes tradename
            if tty == "BN" and not tradename:
                tradename = props[0].get("name")

            # Accumulate synonyms across useful TTYS
            if tty in SYN_TTYS:
                for p in props:
                    name = p.get("name")
                    if name:
                        synonyms.add(name)

    except Exception as e:
        logging.warning("Failed to parse related JSON: %s", e)

    return (ingredient, tradename, sorted(synonyms))

def enrich_one_rxcui(rxcui: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Return (ingredient, tradename, synonyms_string) for an RxCUI by calling allRelated.json.
    """
    url = f"{RXNAV_BASE}/rxcui/{rxcui}/allRelated.json"
    data = http_get_json(url)
    if not data:
        return (None, None, None)

    ingredient, tradename, synonyms = parse_related_for_enrichment(data)

    # Join synonyms into a pipe-separated string; keep it <= ~60k just in case
    syn_str = None
    if synonyms:
        # de-duplicate case-insensitively while preserving first occurrence
        seen_lower = set()
        clean = []
        for s in synonyms:
            k = s.lower()
            if k not in seen_lower:
                seen_lower.add(k)
                clean.append(s)
        syn_str = " | ".join(clean)
        if len(syn_str) > 60000:
            syn_str = syn_str[:60000]

    return (ingredient, tradename, syn_str)

def upsert_enrichments(conn, rows: List[Tuple[int, Optional[str], Optional[str], Optional[str]]]):
    """
    Upsert into drugs by id: ingredient, tradename, rxnorm_synonyms.
    """
    if not rows:
        return

    # Only include columns that actually exist
    cols = fetch_columns(conn, "drugs")
    use_ingredient = "ingredient" in cols
    use_tradename = "tradename" in cols
    use_synonyms = "rxnorm_synonyms" in cols

    if not (use_ingredient or use_tradename or use_synonyms):
        logging.info("No target columns found (ingredient/tradename/rxnorm_synonyms). Nothing to upsert.")
        return

    fields = ["id"]
    if use_ingredient: fields.append("ingredient")
    if use_tradename: fields.append("tradename")
    if use_synonyms:  fields.append("rxnorm_synonyms")

    # Build VALUES tuples with None for missing selected fields
    values = []
    for (drug_id, ing, bn, syn) in rows:
        row_out = [drug_id]
        if use_ingredient: row_out.append(ing)
        if use_tradename: row_out.append(bn)
        if use_synonyms:  row_out.append(syn)
        values.append(tuple(row_out))

    # Build dynamic ON CONFLICT update set
    update_parts = []
    if use_ingredient:
        update_parts.append("ingredient = COALESCE(EXCLUDED.ingredient, drugs.ingredient)")
    if use_tradename:
        update_parts.append("tradename = COALESCE(EXCLUDED.tradename, drugs.tradename)")
    if use_synonyms:
        update_parts.append("rxnorm_synonyms = COALESCE(EXCLUDED.rxnorm_synonyms, drugs.rxnorm_synonyms)")

    update_sql = ", ".join(update_parts)

    query = f"""
        INSERT INTO drugs ({", ".join(fields)})
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            {update_sql}
    """

    with conn.cursor() as cur:
        extras.execute_values(cur, query, values, page_size=500)
    conn.commit()

def main():
    logging.info("Starting RxNorm enrichment (limit=%s)", MAX_ROWS)
    conn = get_db_connection()
    try:
        targets = select_rows_to_enrich(conn, MAX_ROWS)
        if not targets:
            logging.info("No rows need RxNorm enrichment.")
            return

        logging.info("Found %d rows to enrich.", len(targets))

        enriched: List[Tuple[int, Optional[str], Optional[str], Optional[str]]] = []
        processed = 0
        for (drug_id, rxcui) in targets:
            processed += 1
            if processed % 25 == 0:
                logging.info("Progress %d/%d...", processed, len(targets))
            ing, bn, syn = enrich_one_rxcui(str(rxcui))
            enriched.append((drug_id, ing, bn, syn))
            time.sleep(SLEEP_BETWEEN_CALLS)  # gentle pacing

        # Optional: drop rows where we didn't find *anything* (to avoid writing no-ops)
        to_write = [r for r in enriched if any(r[1:])]

        logging.info("Upserting %d/%d rows with non-empty updates...", len(to_write), len(enriched))
        upsert_enrichments(conn, to_write)
        logging.info("RxNorm enrichment completed successfully.")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
