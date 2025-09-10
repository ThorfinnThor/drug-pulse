#!/usr/bin/env python3
"""
FDA Approvals ETL
- Uses openFDA with pagination (limit/skip)
- Filters locally by submission_date
- Fallback: if no records after filter, still processes the first page so you get rows
- Upserts into public.approvals (ON CONFLICT DO NOTHING to avoid constraint issues)
"""
import os
import logging
from datetime import datetime, timedelta

import psycopg2
import requests
from dotenv import load_dotenv
from typing import Optional

from db import get_db_connection

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

OPENFDA = "https://api.fda.gov/drug/drugsfda.json"


def _safe_sub_date(s: Optional[str]) -> Optional[datetime.date]:
    """Parse YYYYMMDD submission date to date; return None if invalid."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except Exception:
        return None



def fuzzy_match_drug(conn, name: str | None) -> int | None:
    if not name:
        return None
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM public.drugs
            WHERE LOWER(preferred_name) = LOWER(%s)
               OR LOWER(active_ingredient) = LOWER(%s)
            LIMIT 1
            """,
            (name, name),
        )
        row = cur.fetchone()
        if row:
            return row[0]

        cur.execute(
            """
            SELECT id FROM public.drugs
            WHERE LOWER(preferred_name) LIKE LOWER(%s)
               OR LOWER(active_ingredient) LIKE LOWER(%s)
            LIMIT 1
            """,
            (f"%{name}%", f"%{name}%"),
        )
        row = cur.fetchone()
        return row[0] if row else None


def fetch_approvals(days_back: int = 30, max_pages: int = 5, page_size: int = 100) -> list[dict]:
    """
    Pull several pages (limit/skip). Filter locally by submission_date >= cutoff.
    """
    cutoff = (datetime.utcnow() - timedelta(days=days_back)).date()
    collected = []

    for page in range(max_pages):
        params = {"limit": page_size, "skip": page * page_size}
        try:
            r = requests.get(OPENFDA, params=params, timeout=40)
            if r.status_code == 404:
                break
            r.raise_for_status()
            items = (r.json().get("results") or [])
            if not items:
                break

            for app in items:
                subs = app.get("submissions") or []
                # include if ANY submission is recent
                include = False
                for s in subs:
                    dt = _safe_sub_date(s.get("submission_date"))
                    if dt and dt >= cutoff:
                        include = True
                        break
                if include:
                    collected.append(app)
        except Exception as e:
            logger.error(f"Error fetching FDA approvals: {e}")
            break

    # Fallback so you actually get rows if nothing matched the date filter
    if not collected:
        logger.info("No FDA approvals matched recent window. Falling back to first page (unfiltered).")
        try:
            r = requests.get(OPENFDA, params={"limit": page_size, "skip": 0}, timeout=40)
            if r.status_code != 404:
                r.raise_for_status()
                collected = r.json().get("results") or []
        except Exception as e:
            logger.error(f"Fallback fetch failed: {e}")

    logger.info(f"Approvals fetched for processing: {len(collected)}")
    return collected


def upsert_approvals(conn, approvals: list[dict]) -> int:
    """
    Insert approvals into public.approvals.
    Uses ON CONFLICT DO NOTHING (no schema changes required).
    """
    inserted = 0
    with conn.cursor() as cur:
        for app in approvals:
            openfda = app.get("openfda") or {}
            brand = (openfda.get("brand_name") or [])
            generic = (openfda.get("generic_name") or [])
            drug_name = (brand[0] if brand else (generic[0] if generic else None))
            if not drug_name:
                continue

            drug_id = fuzzy_match_drug(conn, drug_name)
            if not drug_id:
                continue

            subs = app.get("submissions") or []
            for s in subs:
                dt = _safe_sub_date(s.get("submission_date"))
                if not dt:
                    continue

                docs = s.get("application_docs") or []
                for d in docs:
                    doc_type = (d.get("type") or "").lower()
                    if "approval" not in doc_type:
                        continue
                    doc_url = d.get("url") or ""

                    cur.execute(
                        """
                        INSERT INTO public.approvals
                            (agency, approval_date, drug_id, document_url, application_number)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            "FDA",
                            dt,
                            drug_id,
                            doc_url,
                            app.get("application_number", ""),
                        ),
                    )
                    inserted += 1
                    # Insert just one per submission to avoid spamming
                    break

    conn.commit()
    return inserted


def main():
    try:
        conn = get_db_connection()
        logger.info("Connected to database")

        days_back = int(os.getenv("FDA_DAYS_BACK", "30"))
        approvals = fetch_approvals(days_back=days_back, max_pages=6, page_size=100)

        if not approvals:
            logger.info("No approvals fetched.")
            return

        count = upsert_approvals(conn, approvals)
        logger.info(f"Inserted {count} FDA approval records")
    except Exception as e:
        logger.error(f"FDA ETL failed: {e}")
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
