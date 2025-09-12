#!/usr/bin/env python3
"""
drugs_rxnorm_enrich.py
----------------------
Enrich drugs with ingredient, tradename, and synonyms using RxNorm.
- Try allRelated.json
- If empty → try related.json
- If still missing ingredient → explicitly query /related.json?tty=IN
- If all fail → fallback to properties.json
Writes updates in batches to avoid SSL EOF issues.
Prints a summary at the end of the run.
"""

import os
import time
import logging
import psycopg2
from psycopg2 import extras
import requests
from collections import Counter

# -------------------------
# Config
# -------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
LIMIT = int(os.getenv("RXNORM_ENRICH_LIMIT", "100"))
SLEEP_BETWEEN_CALLS = float(os.getenv("RXNORM_SLEEP", "0.1"))
BATCH_SIZE = int(os.getenv("RXNORM_BATCH_SIZE", "200"))
SYN_TTYS = {"BN", "SBD", "SCD", "IN", "PIN", "MIN"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# -------------------------
# DB helpers
# -------------------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def select_rows_to_enrich(conn, limit):
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


def upsert_enrichments(conn, rows, batch_size=BATCH_SIZE):
    """Upsert enrichment data in smaller batches to avoid SSL EOF issues."""
    if not rows:
        logger.info("No enrichment updates to write.")
        return

    query = """
        UPDATE drugs AS d
        SET
            ingredient = COALESCE(data.ingredient, d.ingredient),
            tradename = COALESCE(data.tradename, d.tradename),
            rxnorm_synonyms = COALESCE(data.synonyms, d.rxnorm_synonyms)
        FROM (VALUES %s) AS data(id, ingredient, tradename, synonyms)
        WHERE d.id = data.id::int
    """

    with conn.cursor() as cur:
        for i in range(0, len(rows), batch_size):
            chunk = rows[i:i + batch_size]
            extras.execute_values(cur, query, chunk, page_size=batch_size)
    conn.commit()
    logger.info("✅ Updated %d drugs with ingredient/tradename/synonyms (in batches of %d)", len(rows), batch_size)


# -------------------------
# RxNorm helpers
# -------------------------
def http_get_json(url: str):
    try:
        resp = requests.get(url, timeout=12, headers={"User-Agent": "pharmaintel/1.0"})
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return None
        logger.warning("RxNav non-200 (%s) for %s", resp.status_code, url)
    except requests.RequestException as e:
        logger.warning("RxNav request failed (%s) for %s", e, url)
    return None


def parse_concepts(concept_groups):
    ingredient, tradename = None, None
    synonyms = set()

    for grp in concept_groups:
        tty = (grp.get("tty") or "").upper().strip()
        props = grp.get("conceptProperties") or []
        for p in props:
            name = p.get("name")
            if not name:
                continue
            if tty == "IN" and not ingredient:
                ingredient = name
            if tty == "BN" and not tradename:
                tradename = name
            if tty in SYN_TTYS:
                synonyms.add(name)

    syn_str = " | ".join(sorted(synonyms)) if synonyms else None
    return ingredient, tradename, syn_str


def fallback_to_ingredient(rxcui: str):
    """Explicitly query ingredient if not found in normal enrichment."""
    url = f"{RXNAV_BASE}/rxcui/{rxcui}/related.json?tty=IN"
    data = http_get_json(url)
    if data and "relatedGroup" in data:
        groups = data["relatedGroup"].get("conceptGroup", [])
        ing, _, _ = parse_concepts(groups)
        if ing:
            logger.info("Resolved ingredient for RxCUI %s via related.json?tty=IN", rxcui)
            return ing
    return None


def enrich_one_rxcui(rxcui, stats: Counter):
    # 1) Try allRelated.json
    data = http_get_json(f"{RXNAV_BASE}/rxcui/{rxcui}/allRelated.json")
    if data and "allRelatedGroup" in data:
        groups = data["allRelatedGroup"].get("conceptGroup", [])
        if groups:
            ing, bn, syn = parse_concepts(groups)
            if not ing:
                ing = fallback_to_ingredient(rxcui)
                if ing:
                    stats["ingredient_fallback"] += 1
            if any([ing, bn, syn]):
                stats["allRelated"] += 1
                return ing, bn, syn

    # 2) Fallback: related.json
    data = http_get_json(f"{RXNAV_BASE}/rxcui/{rxcui}/related.json?tty=IN+BN+SCD+SBD")
    if data and "relatedGroup" in data:
        groups = data["relatedGroup"].get("conceptGroup", [])
        if groups:
            ing, bn, syn = parse_concepts(groups)
            if not ing:
                ing = fallback_to_ingredient(rxcui)
                if ing:
                    stats["ingredient_fallback"] += 1
            if any([ing, bn, syn]):
                stats["related"] += 1
                return ing, bn, syn

    # 3) Fallback: properties.json
    data = http_get_json(f"{RXNAV_BASE}/rxcui/{rxcui}/properties.json")
    if data and "properties" in data:
        name = data["properties"].get("name")
        if name:
            stats["properties"] += 1
            return None, None, name

    stats["none"] += 1
    return None, None, None


# -------------------------
# Main ETL
# -------------------------
def main():
    conn = get_db_connection()
    stats = Counter()

    try:
        targets = select_rows_to_enrich(conn, LIMIT)
        logger.info("Found %d drugs to enrich", len(targets))

        enriched = []
        for (drug_id, rxcui) in targets:
            ing, bn, syn = enrich_one_rxcui(str(rxcui), stats)
            if any([ing, bn, syn]):
                enriched.append((drug_id, ing, bn, syn))
            time.sleep(SLEEP_BETWEEN_CALLS)

        upsert_enrichments(conn, enriched, batch_size=BATCH_SIZE)

        # --- Summary report ---
        logger.info("=== Enrichment Summary ===")
        logger.info("allRelated.json        : %d", stats["allRelated"])
        logger.info("related.json           : %d", stats["related"])
        logger.info("ingredient_fallback    : %d", stats["ingredient_fallback"])
        logger.info("properties.json        : %d", stats["properties"])
        logger.info("no data                : %d", stats["none"])

    finally:
        conn.close()


if __name__ == "__main__":
    main()
