import os
import re
import time
import requests
import psycopg2
from psycopg2 import extras
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"
HEADERS = {"Accept": "application/json"}

# --------------------------
# NDC normalization helpers
# --------------------------

NDCP = re.compile(r"^\d+-\d+(?:-\d+)?$")

def strip_hyphens(s: str) -> str:
    return s.replace("-", "") if s else s

def pad_left(s: str, n: int) -> str:
    return s.zfill(n)

def normalize_candidates(product_ndc: str | None, package_ndc: str | None) -> list[str]:
    """
    Build a list of plausible NDC strings (hyphenated and hyphenless)
    that RxNav is likely to accept.
    Priority: package_ndc (if present), otherwise try expansions from product_ndc.
    """
    cands: list[str] = []

    # 1) If we have a package_ndc already (e.g., 58159-067-01), use it first.
    if package_ndc and NDCP.match(package_ndc):
        cands.append(package_ndc)

    # 2) Expand product_ndc (e.g., 58159-067 or 37662-2258) to likely 10/11-digit variants.
    if product_ndc and NDCP.match(product_ndc):
        parts = product_ndc.split("-")
        if len(parts) == 2:
            a, b = parts
            if len(a) == 5 and len(b) == 3:
                # 5-3 → 5-3-2 (10-digit) + 11-digit padded 5-4-2
                cands.append(f"{a}-{b}-01")                    # 10-digit style
                cands.append(f"{a}-{pad_left(b,4)}-01")        # 11-digit style
            elif len(a) == 5 and len(b) == 4:
                # 5-4 → 5-4-2
                cands.append(f"{a}-{b}-01")                    # 11-digit already
            elif len(a) == 4 and len(b) == 4:
                # 4-4 → 4-4-2 (10-digit) + try 0-prefixed 11-digit 5-4-2
                cands.append(f"{a}-{b}-01")                    # 10-digit
                cands.append(f"{pad_left(a,5)}-{b}-01")        # 11-digit (prefix 0)
            else:
                # Unknown two-part shape; still try adding -01
                cands.append(f"{a}-{b}-01")
        elif len(parts) == 3:
            # Already has 3 parts; try as-is
            cands.append(product_ndc)

    # Deduplicate while preserving order
    seen = set()
    hyphenated = []
    for x in cands:
        if x and x not in seen:
            seen.add(x)
            hyphenated.append(x)

    # Add hyphenless variants for each hyphenated candidate
    final = []
    seen.clear()
    for x in hyphenated:
        if x not in seen:
            seen.add(x)
            final.append(x)
        no_dash = strip_hyphens(x)
        if no_dash and no_dash not in seen:
            seen.add(no_dash)
            final.append(no_dash)

    return final

# --------------------------
# RxNav queries (robust)
# --------------------------

def _is_json(resp: requests.Response) -> bool:
    ctype = resp.headers.get("content-type", "").lower()
    return "application/json" in ctype

def _get_rxcui_from_payload(data: dict) -> str | None:
    # common shapes seen from RxNav
    if isinstance(data, dict):
        ig = data.get("idGroup", {})
        ids = ig.get("rxnormId")
        if ids and isinstance(ids, list) and ids[0]:
            return ids[0]
        # fallback if endpoint returns { "rxcui": "xxxxx" }
        rc = data.get("rxcui")
        if rc:
            return rc
    return None

def fetch_rxcui_for_code(code: str, max_retries: int = 3) -> str | None:
    """
    Try multiple endpoints and retry on 429/5xx or non-JSON responses.
    """
    urls = [
        f"{RXNORM_BASE}/rxcui.json?ndc={code}",
        f"{RXNORM_BASE}/rxcui?idtype=ndc&id={code}",
    ]
    backoff = 1.0

    for attempt in range(max_retries):
        for url in urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=12)
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(backoff)
                    continue
                if resp.status_code == 404:
                    continue
                if not _is_json(resp):
                    # RxNav sometimes serves an HTML page on error
                    continue
                data = resp.json()
                rxcui = _get_rxcui_from_payload(data)
                if rxcui:
                    return rxcui
            except requests.RequestException:
                time.sleep(backoff)
                continue
            except ValueError:
                # JSON decode error
                time.sleep(backoff)
                continue
        backoff = min(backoff * 2, 8.0)

    return None

def resolve_ndc_to_rxcui(product_ndc: str | None, package_ndc: str | None) -> str | None:
    for cand in normalize_candidates(product_ndc, package_ndc):
        rxcui = fetch_rxcui_for_code(cand)
        if rxcui:
            return rxcui
    return None

# --------------------------
# DB operations
# --------------------------

def get_rows_to_enrich(conn):
    """
    Pull product_ndc + package_ndc for drugs with missing rxcui.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT product_ndc, package_ndc
            FROM drugs
            WHERE rxcui IS NULL AND product_ndc IS NOT NULL
        """)
        return cur.fetchall()

def upsert_rxcui(pairs, conn):
    """
    pairs: List of tuples (product_ndc, rxcui)
    Only update rows where we found an rxcui.
    """
    rows = [(p, r) for (p, r) in pairs if r]
    if not rows:
        return
    with conn.cursor() as cur:
        query = """
            UPDATE drugs
            SET rxcui = data.rxcui
            FROM (VALUES %s) AS data(product_ndc, rxcui)
            WHERE drugs.product_ndc = data.product_ndc;
        """
        extras.execute_values(cur, query, rows, page_size=500)
    conn.commit()

# --------------------------
# Orchestration
# --------------------------

def enrich_rxnorm(workers: int = 12):
    conn = psycopg2.connect(DATABASE_URL)
    try:
        todo = get_rows_to_enrich(conn)
        total = len(todo)
        print(f"🔍 Found {total} NDCs to enrich with RxNorm")

        results = []
        # Limit concurrency a bit to avoid throttling
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = []
            for product_ndc, package_ndc in todo:
                futures.append(
                    pool.submit(
                        resolve_ndc_to_rxcui, product_ndc, package_ndc
                    )
                )

            for i, fut in enumerate(as_completed(futures), 1):
                rxcui = fut.result()
                # Map back to the corresponding input
                product_ndc, package_ndc = todo[len(results)]
                results.append((product_ndc, rxcui))
                if i % 500 == 0 or i == total:
                    print(f"…processed {i}/{total}")

        upsert_rxcui(results, conn)
        found = sum(1 for _, r in results if r)
        print(f"✅ RxNorm enrichment complete. Matched {found}/{total}.")

    finally:
        conn.close()

if __name__ == "__main__":
    enrich_rxnorm()
