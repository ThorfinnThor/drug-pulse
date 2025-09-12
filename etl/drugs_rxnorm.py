#!/usr/bin/env python3
"""
drugs_rxnorm.py
---------------
Populate drugs.rxnorm_id using RxNav.
Strategy:
  1) Try NDC → RxCUI (most reliable)
  2) Fallback to approximateTerm(name) → RxCUI
Updates are written in batches to avoid connection resets.
"""

import os
import re
import time
import logging
from typing import Iterable, List, Optional, Tuple

import requests
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

# -------------------------
# Config
# -------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
LIMIT = int(os.getenv("RXNORM_LIMIT", "100"))      # number of rows to attempt per run
HTTP_TIMEOUT = float(os.getenv("RXNORM_HTTP_TIMEOUT", "12"))
SLEEP = float(os.getenv("RXNORM_SLEEP", "0.10"))   # polite delay between HTTP calls

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("drugs_rxnorm")


# -------------------------
# DB helpers
# -------------------------
def get_db() -> psycopg2.extensions.connection:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL)


def fetch_targets(conn, limit: int) -> List[dict]:
    """Rows missing rxnorm_id but with something we can use (NDC or a name)."""
    with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, product_ndc, preferred_name, generic_name, brand_name
            FROM drugs
            WHERE rxnorm_id IS NULL
              AND (product_ndc IS NOT NULL OR preferred_name IS NOT NULL
                   OR generic_name IS NOT NULL OR brand_name IS NOT NULL)
            ORDER BY id
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()


def update_rxnorm_ids(conn, rows: List[Tuple[int, str]], batch_size: int = 200) -> None:
    """Bulk set rxnorm_id for the given (id, rxnorm_id) tuples in smaller batches."""
    if not rows:
        log.info("Nothing to update.")
        return

    query = """
        UPDATE drugs AS d
        SET rxnorm_id = data.rxnorm_id
        FROM (VALUES %s) AS data(id, rxnorm_id)
        WHERE d.id = data.id::int
    """

    with conn.cursor() as cur:
        for i in range(0, len(rows), batch_size):
            chunk = rows[i:i + batch_size]
            extras.execute_values(cur, query, chunk, page_size=batch_size)
    conn.commit()
    log.info("✅ Set rxnorm_id for %d rows (in batches of %d)", len(rows), batch_size)


# -------------------------
# RxNav helpers
# -------------------------
def http_get_json(url: str) -> Optional[dict]:
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": "pharmaintel/1.0"})
        if r.status_code == 200:
            return r.json()
        log.debug("RxNav non-200 %s for %s", r.status_code, url)
    except requests.RequestException as e:
        log.debug("RxNav error %s for %s", e, url)
    return None


def normalize_ndc_candidates(ndc_raw: str) -> Iterable[str]:
    """Produce common NDC formats to maximize hit rate."""
    if not ndc_raw:
        return []
    s = re.sub(r"[^0-9]", "", ndc_raw)
    cands = set()

    if len(s) in (10, 11):
        # digits-only
        cands.add(s)

        if len(s) == 11:
            # hyphenated 5-4-2
            a, b, c = s[:5], s[5:9], s[9:]
            cands.add(f"{a}-{b}-{c}")
        elif len(s) == 10:
            # try 4-4-2, 5-3-2, 5-4-1
            cands.add(f"{s[:4]}-{s[4:8]}-{s[8:]}")
            cands.add(f"{s[:5]}-{s[5:8]}-{s[8:]}")
            cands.add(f"{s[:5]}-{s[5:9]}-{s[9:]}")
    return cands


def rxcui_from_ndc(ndc: str) -> Optional[str]:
    """NDC → RxCUI via /rxcui.json?ndc="""
    for cand in normalize_ndc_candidates(ndc):
        url = f"{RXNAV_BASE}/rxcui.json?ndc={cand}"
        data = http_get_json(url)
        if not data:
            continue
        rid = (data.get("idGroup") or {}).get("rxnormId")
        if rid and len(rid) > 0:
            return str(rid[0])
    return None


def clean_name(name: str) -> str:
    """Strip strengths/forms to help approximateTerm hit."""
    if not name:
        return ""
    s = name
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|g|iu|ml|mL|%|units)\b", " ", s, flags=re.I)
    s = re.sub(r"\b(oral|tablet|capsule|solution|suspension|injection|spray|ointment|cream|patch|gel|extended release|er|xr)\b", " ", s, flags=re.I)
    s = re.sub(r"[^A-Za-z0-9\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def rxcui_from_name(name: str) -> Optional[str]:
    """Name → RxCUI using approximateTerm (forgiving)."""
    if not name:
        return None
    term = clean_name(name)
    if not term:
        return None
    url = f"{RXNAV_BASE}/approximateTerm.json?term={requests.utils.quote(term)}&maxEntries=1"
    data = http_get_json(url)
    if not data:
        return None
    try:
        cands = ((data.get("approximateGroup") or {}).get("candidate")) or []
        if not cands:
            return None
        return str(cands[0]["rxcui"])
    except Exception:
        return None


# -------------------------
# Main
# -------------------------
def main():
    conn = get_db()
    try:
        rows = fetch_targets(conn, LIMIT)
        log.info("Found %d rows to resolve (limit=%d)", len(rows), LIMIT)

        updates: List[Tuple[int, str]] = []

        for d in rows:
            drug_id = d["id"]
            ndc = d.get("product_ndc")
            name = d.get("preferred_name") or d.get("generic_name") or d.get("brand_name")

            rxcui: Optional[str] = None

            # 1) NDC → RxCUI
            if ndc:
                rxcui = rxcui_from_ndc(ndc)

            # 2) Fallback: approximateTerm(name)
            if not rxcui and name:
                rxcui = rxcui_from_name(name)

            if rxcui:
                updates.append((drug_id, rxcui))

            time.sleep(SLEEP)

        # Only write rows where we actually found an RxCUI
        update_rxnorm_ids(conn, updates)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
