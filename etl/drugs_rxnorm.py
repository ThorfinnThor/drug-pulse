#!/usr/bin/env python3
"""
RxNorm Enrichment ETL Script
Enriches drugs in the database with RxNorm IDs, brand/generic names, synonyms.
Falls back to FDA NDC fields if RxNorm is incomplete.
"""

import os
import requests
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
import logging
import time

# =========================
# CONFIG
# =========================
LIMIT = 100  # set limit for number of drugs per run
RXNORM_API = "https://rxnav.nlm.nih.gov/REST"

# Load env vars
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# =========================
# DB Helpers
# =========================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def fetch_drugs_without_rxnorm(conn, limit=LIMIT):
    """Fetch drugs missing RxNorm ID or names"""
    with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, preferred_name, generic_name, brand_name, rxcui, product_ndc
            FROM drugs
            WHERE rxcui IS NULL OR generic_name IS NULL OR brand_name IS NULL
            LIMIT %s
            """,
            (limit,)
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
            rxcui = data.rxcui,
            brand_name = COALESCE(data.brand_name, d.brand_name),
            generic_name = COALESCE(data.generic_name, d.generic_name),
            preferred_name = COALESCE(data.preferred_name, d.preferred_name),
            synonyms = COALESCE(data.synonyms, d.synonyms)
        FROM (VALUES %s) AS data(id, rxcui, brand_name, generic_name, preferred_name, synonyms)
        WHERE d.id = data.id::int
        """
        values = [
            (
                d["id"],
                d.get("rxcui"),
                d.get("brand_name"),
                d.get("generic_name"),
                d.get("preferred_name"),
                d.get("synonyms"),
            )
            for d in rows
        ]
        extras.execute_values(cur, query, values)
    conn.commit()
    logger.info(f"✅ Updated {len(rows)} drugs with RxNorm/FDA data")


# =========================
# RxNorm API Helpers
# =========================
def get_rxcui_by_name(name):
    """Get RxCUI for a given drug name"""
    if not name:
        return None
    url = f"{RXNORM_API}/rxcui.json?name={requests.utils.quote(name)}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("idGroup", {}).get("rxnormId", [None])[0]
    except Exception:
        return None


def parse_rxnorm_names(rxcui):
    """Fetch brand, generic, preferred name, and synonyms from RxNorm"""
    if not rxcui:
        return None, None, None, None

    url = f"{RXNORM_API}/rxcui/{rxcui}/allProperties.json?prop=names"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None, None, None, None
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
            elif tty == "IN" and not generic_name:
                generic_name = name

        preferred_name = generic_name or brand_name or (synonyms[0] if synonyms else None)

        return brand_name, generic_name, preferred_name, ", ".join(synonyms) if synonyms else None

    except Exception:
        return None, None, None, None


# =========================
# Main ETL
# =========================
def main():
    conn = get_db_connection()
    try:
        drugs = fetch_drugs_without_rxnorm(conn, LIMIT)
        logger.info(f"Found {len(drugs)} drugs to enrich")

        enriched = []
        for d in drugs:
            name = d["preferred_name"] or d["generic_name"] or d["brand_name"]
            if not name:
                continue

            # 1️⃣ Try RxNorm lookup
            rxcui = d.get("rxcui") or get_rxcui_by_name(name)
            brand_name, generic_name, preferred_name, synonyms = (None, None, None, None)
            if rxcui:
                brand_name, generic_name, preferred_name, synonyms = parse_rxnorm_names(rxcui)

            # 2️⃣ Fallback to FDA NDC fields if RxNorm is missing
            if not brand_name and d.get("brand_name"):
                brand_name = d["brand_name"]
            if not generic_name and d.get("generic_name"):
                generic_name = d["generic_name"]
            if not preferred_name:
                preferred_name = brand_name or generic_name or d.get("preferred_name")

            enriched.append({
                "id": d["id"],
                "rxcui": rxcui,
                "brand_name": brand_name,
                "generic_name": generic_name,
                "preferred_name": preferred_name,
                "synonyms": synonyms
            })

            time.sleep(0.2)  # avoid API rate limit

        upsert_rxnorm_data(conn, enriched)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
