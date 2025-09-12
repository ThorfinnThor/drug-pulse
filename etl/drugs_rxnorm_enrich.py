#!/usr/bin/env python3
"""
drugs_rxnorm_enrich.py
----------------------
Enrich drugs with ingredient, tradename, and synonyms using RxNorm.
- Try allRelated.json
- If 404 or empty, fallback to related.json
- If still empty, fallback to properties.json
Logs which source was used.
"""

import os
import time
import logging
import psycopg2
from psycopg2 import extras
import requests

DATABASE_URL = os.getenv("DATABASE_URL")
RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
LIMIT = int(os.getenv("RXNORM_ENRICH_LIMIT", "1000"))
SLEEP_BETWEEN_CALLS = float(os.getenv("RXNORM_SLEEP", "0.1"))
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


def upsert_enrichments(conn, rows):
    if not rows:
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
        extras.execute_values(cur, query, rows, page_size=500)
    conn.commit()
    logger.info("✅ Updated %d drugs with ingredient/tradename/synonyms", len(rows))


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


def enrich_one_rxcui(rxcui):
    # 1) Try allRelated.json
    url1 = f"{RXNAV_BASE}/rxcui/{rxcui}/allRelated.json"
    data = http_get_json(url1)
    if data and "allRelatedGroup" in data:
        groups = data["allRelatedGroup"].get("conceptGroup", [])
        if groups:
            logger.info("Enriched RxCUI %s via allRelated.json", rxcui)
            return parse_concepts(groups)

    # 2) Fallback: related.json with specific TTYS
    url2 = f"{RXNAV_BASE}/rxcui/{rxcui}/related.json?tty=IN+BN+SCD+SBD"
    data = http_get_json(url2)
    if data and "relatedGroup" in data:
        groups = data["relatedGroup"].get("conceptGroup", [])
        if groups:
            logger.info("Enriched RxCUI %s via related.json", rxcui)
            return parse_concepts(groups)

    # 3) Fallback: properties.json
    url3 = f"{RXNAV_BASE}/rxcui/{rxcui}/properties.json"
    data = http_get_json(url3)
    if data and "properties" in data:
        name = data["properties"].get("name")
        if name:
            logger.info("Enriched RxCUI %s via properties.json", rxcui)
            return None, None, name

    logger.warning("No enrichment data for RxCUI %s", rxcui)
    return None, None, None


# -------------------------
# Main ETL
# -------------------------
def main():
    conn = get_db_connection()
    try:
        targets = select_rows_to_enrich(conn, LIMIT)
        logger.info("Found %d drugs to enrich", len(targets))

        enriched = []
        for (drug_id, rxcui) in targets:
            ing, bn, syn = enrich_one_rxcui(str(rxcui))
            if any([ing, bn, syn]):
                enriched.append((drug_id, ing, bn, syn))
            time.sleep(SLEEP_BETWEEN_CALLS)

        upsert_enrichments(conn, enriched)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
