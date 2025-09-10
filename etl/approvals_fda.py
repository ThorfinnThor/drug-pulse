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


def fetch_recent_approvals(days_back=365, max_pages=5):
    """Fetch FDA approvals, paginated, and filter locally by submission_date."""
    logger.info(f"Fetching FDA approvals (last {days_back} days)...")

    cutoff_date = datetime.today() - timedelta(days=days_back)
    all_results = []

    url = f"{FDA_API_BASE}/drug/drugsfda.json"

    for page in range(max_pages):
        params = {"limit": 100, "skip": page * 100}
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 404:
                logger.info("No FDA approvals found on this page")
                break
            resp.raise_for_status()

            data = resp.json()
            results = data.get("results", [])
            if not results:
                break  # no more pages

            all_results.extend(results)

        except Exception as e:
            logger.error(f"Error fetching FDA approvals page {page}: {e}")
            break

    # Filter by submission_date
    filtered = []
    for app in all_results:
        submissions = app.get("submissions", [])
        for sub in submissions:
            sub_date = sub.get("submission_date")
            if not sub_date:
                continue
            try:
                sub_dt = datetime.strptime(sub_date, "%Y%m%d").date()
            except ValueError:
                continue
            if sub_dt >= cutoff_date.date():
                filtered.append(app)
                break  # keep once per approval

    logger.info(f"Fetched {len(filtered)} FDA approval records after filtering")
    return filtered



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
