#!/usr/bin/env python3
"""
drugs_rxnorm_enrich.py
----------------------
Enrich drugs with ingredient, tradename, and synonyms using RxNorm allRelated.json.
"""

import os
import time
import logging
import psycopg2
from psycopg2 import extras
import requests

# -------------------------
# Config
# -------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
LIMIT = int(os.getenv("RXNORM_ENRICH_LIMIT", "100"))
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

    values = [
        (drug_id, ing, bn, syn)
        for (drug_id, ing, bn, syn) in rows
    ]

    with conn.cursor() as cur:
        extras.execute_values(cur, query, values)
    conn.commit()
    logger.info(f"✅ Updated {len(rows)} drugs with ingredient/tradename/synonyms")


# -------------------------
# RxNorm helpers
# -------------------------
def http_get_json(url: str):
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "drug-pulse/1.0"})
        if resp.status_code == 200:
            return resp.json()
        logger.warning("RxNav non-200 (%s) for %s", resp.status_code, url)
    except requests.RequestException as e:
        logger.warning("RxNav request failed (%s) for %s", e, url)
    return None


def parse_related_for_enrichment(data):
    ingredient, tradename = None, None
    synonyms = set()

    groups = data.get("allRelatedGroup", {}).get("conceptGroup", [])
    for grp in groups:
        tty = (grp.get("tty") or "").upper().strip()
        props = grp.get("conceptProperties") or []
        if not props:
            continue

        if tty == "IN" and not ingredient:
            ingredient = props[0].get("name")
        if tty == "PIN" and not ingredient:
            ingredient = props[0].get("name")
        if tty == "BN" and not tradename:
            tradename = props[0].get("name")

        if tty in SYN_TTYS:
            for p in props:
                name = p.get("name")
                if name:
                    synonyms.add(name)

    syn_str = " | ".join(sorted(synonyms)) if synonyms else None
    return ingredient, tradename, syn_str


def enrich_one_rxcui(rxcui):
    url = f"{RXNAV_BASE}/rxcui/{rxcui}/allRelated.json"
    data = http_get_json(url)
    if not data:
        return None, None, None
    return parse_related_for_enrichment(data)


# -------------------------
# Main ETL
# -------------------------
def main():
    conn = get_db_connection()
    try:
        targets = select_rows_to_enrich(conn, LIMIT)
        logger.info(f"Found {len(targets)} drugs to enrich")

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
