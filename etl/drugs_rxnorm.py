#!/usr/bin/env python3
"""
drugs_rxnorm.py
---------------
Resolve RxNorm IDs (RxCUI) for drugs in the DB using RxNav API.
Populates: rxnorm_id, brand_name, generic_name, synonyms.
Keeps FDA preferred_name untouched.
"""

import os
import time
import logging
import requests
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

# -------------------------
# Config
# -------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
RXNORM_API = "https://rxnav.nlm.nih.gov/REST"
LIMIT = int(os.getenv("RXNORM_LIMIT", "100"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# -------------------------
# DB helpers
# -------------------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def fetch_drugs_without_rxnorm(conn, limit=LIMIT):
    """Fetch drugs missing RxNorm ID"""
    with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, preferred_name, brand_name, generic_name
            FROM drugs
            WHERE rxnorm_id IS NULL
            ORDER BY id
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()


def upsert_rxnorm_data(conn, rows):
    """Bulk update drugs with RxNorm data"""
    if not rows:
        return

    with conn.cursor() as cur:
        query = """
        UPDATE drugs AS d
        SET
            rxnorm_id = data.rxnorm_id,
            brand_name = COALESCE(data.brand_name, d.brand_name),
            generic_name = COALESCE(data.generic_name, d.generic_name),
            rxnorm_synonyms = COALESCE(data.synonyms, d.rxnorm_synonyms)
        FROM (VALUES %s) AS data(id, rxnorm_id, brand_name, generic_name, synonyms)
        WHERE d.id = data.id::int
        """
        values = [
            (
                d["id"],
                d.get("rxnorm_id"),
                d.get("brand_name"),
                d.get("generic_name"),
                d.get("synonyms"),
            )
            for d in rows
        ]
        extras.execute_values(cur, query, values)
    conn.commit()
    logger.info(f"✅ Updated {len(rows)} drugs with RxNorm data")


# -------------------------
# RxNorm API helpers
# -------------------------
def get_rxcui_by_name(name):
    """Get RxCUI for a given drug name"""
    if not name:
        return None
    url = f"{RXNORM_API}/rxcui.json?name={requests.utils.quote(name)}"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "drug-pulse/1.0"})
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("idGroup", {}).get("rxnormId", [None])[0]
    except Exception:
        return None


def parse_rxnorm_names(rxcui):
    """Fetch brand, generic, and synonyms from RxNorm"""
    if not rxcui:
        return None, None, None

    url = f"{RXNORM_API}/rxcui/{rxcui}/allProperties.json?prop=names"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "drug-pulse/1.0"})
        if resp.status_code != 200:
            return None, None, None
        data = resp.json()

        synonyms = []
        brand_name, generic_name = None, None

        for entry in data.get("propConceptGroup", {}).get("propConcept", []):
            name = entry.get("propValue")
            tty = entry.get("propCategory") or entry.get("propName")

            if name:
                synonyms.append(name)

            if tty == "BN" and not brand_name:
                brand_name = name
            elif tty in {"IN", "GN"} and not generic_name:
                generic_name = name

        return brand_name, generic_name, ", ".join(synonyms) if synonyms else None

    except Exception:
        return None, None, None


# -------------------------
# Main ETL
# -------------------------
def main():
    conn = get_db_connection()
    try:
        drugs = fetch_drugs_without_rxnorm(conn, LIMIT)
        logger.info(f"Found {len(drugs)} drugs to enrich with RxNorm IDs")

        enriched = []
        for d in drugs:
            name = d["preferred_name"] or d["generic_name"] or d["brand_name"]
            if not name:
                continue

            rxcui = get_rxcui_by_name(name)
            brand_name, generic_name, synonyms = (None, None, None)
            if rxcui:
                brand_name, generic_name, synonyms = parse_rxnorm_names(rxcui)

            enriched.append({
                "id": d["id"],
                "rxnorm_id": rxcui,
                "brand_name": brand_name,
                "generic_name": generic_name,
                "synonyms": synonyms
            })

            time.sleep(0.2)  # polite delay

        upsert_rxnorm_data(conn, enriched)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
