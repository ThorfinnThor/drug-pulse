#!/usr/bin/env python3
"""
ClinicalTrials.gov ETL
- Uses the v2 GET endpoint with minimal params to avoid 400s
- Filters locally by "startDate" to the last N days (configurable)
- Upserts into public.trials (assumes id is the PK on trials.id)
"""
import os
import logging
from datetime import datetime, timedelta

import psycopg2
import requests
from dotenv import load_dotenv

from db import get_db_connection
from typing import Optional

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

CTGOV_V2 = "https://clinicaltrials.gov/api/v2/studies"


def _safe_date(d: Optional[str]) -> Optional[datetime.date]:
    """Parse YYYY-MM-DD to date; return None if invalid."""
    if not d:
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        return None



def _extract_phase(design_module: dict) -> str:
    """
    Extract a compact phase string from the design module.
    design_module.get('phases') is usually a list like ['PHASE1','PHASE2'].
    """
    phases = design_module.get("phases") or []
    if not phases:
        return "N/A"

    # Normalize to integers where possible
    pset = set()
    for p in phases:
        pl = (p or "").lower()
        if "phase 1" in pl or pl == "phase1":
            pset.add("1")
        elif "phase 2" in pl or pl == "phase2":
            pset.add("2")
        elif "phase 3" in pl or pl == "phase3":
            pset.add("3")
        elif "phase 4" in pl or pl == "phase4":
            pset.add("4")

    if not pset:
        return "N/A"
    return "/".join(sorted(pset))


def _fuzzy_match_company(conn, sponsor_name: str | None) -> int | None:
    if not sponsor_name:
        return None
    with conn.cursor() as cur:
        # exact
        cur.execute(
            "SELECT id FROM public.companies WHERE LOWER(canonical_name)=LOWER(%s) LIMIT 1",
            (sponsor_name,),
        )
        row = cur.fetchone()
        if row:
            return row[0]

        # contains
        cur.execute(
            """
            SELECT id FROM public.companies
            WHERE LOWER(canonical_name) LIKE LOWER(%s)
            LIMIT 1
            """,
            (f"%{sponsor_name}%",),
        )
        row = cur.fetchone()
        return row[0] if row else None


def fetch_studies(max_rows: int = 100) -> list[dict]:
    """
    Pull a single page of v2 studies with minimal params.
    This avoids the 400s that show up with certain server-side filter combos.
    We’ll filter locally.
    """
    params = {"pageSize": max_rows}
    try:
        r = requests.get(CTGOV_V2, params=params, timeout=40)
        r.raise_for_status()
        data = r.json()
        studies = data.get("studies", []) or []
        logger.info(f"Fetched {len(studies)} trials (unfiltered).")
        return studies
    except Exception as e:
        logger.error(f"Error fetching trials: {e}")
        return []


def upsert_trials(conn, studies: list[dict], days_back: int = 90) -> int:
    """
    Insert/update trials. We filter locally by start_date within the last N days.
    If no start_date is present, we keep the record (so we still get data).
    """
    keep_after = datetime.utcnow().date() - timedelta(days=days_back)
    inserted = 0

    with conn.cursor() as cur:
        for st in studies:
            protocol = st.get("protocolSection", {})
            ident = protocol.get("identificationModule", {})
            status = protocol.get("statusModule", {})
            design = protocol.get("designModule", {})
            sponsor = protocol.get("sponsorCollaboratorsModule", {})

            nct_id = ident.get("nctId")
            if not nct_id:
                continue

            title = ident.get("briefTitle") or ""
            phase = _extract_phase(design)
            overall_status = status.get("overallStatus") or ""

            start_date = None
            if status.get("startDateStruct"):
                start_date = _safe_date(status["startDateStruct"].get("date"))

            primary_completion_date = None
            if status.get("primaryCompletionDateStruct"):
                primary_completion_date = _safe_date(
                    status["primaryCompletionDateStruct"].get("date")
                )

            sponsor_name = (sponsor.get("leadSponsor") or {}).get("name")
            sponsor_company_id = _fuzzy_match_company(conn, sponsor_name)

            # Local filter: keep if start_date within window OR start_date missing
            if start_date and start_date < keep_after:
                continue

            cur.execute(
                """
                INSERT INTO public.trials
                    (id, title, phase, status, start_date, primary_completion_date,
                     sponsor_company_id, last_updated, fetched_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    phase = EXCLUDED.phase,
                    status = EXCLUDED.status,
                    start_date = EXCLUDED.start_date,
                    primary_completion_date = EXCLUDED.primary_completion_date,
                    sponsor_company_id = EXCLUDED.sponsor_company_id,
                    last_updated = EXCLUDED.last_updated,
                    fetched_at = EXCLUDED.fetched_at
                """,
                (
                    nct_id,
                    title,
                    phase,
                    overall_status,
                    start_date,
                    primary_completion_date,
                    sponsor_company_id,
                    datetime.utcnow(),
                    datetime.utcnow(),
                ),
            )
            inserted += 1

    conn.commit()
    return inserted


def main():
    try:
        conn = get_db_connection()
        logger.info("Connected to database")

        days_back = int(os.getenv("CTGOV_DAYS_BACK", "90"))
        studies = fetch_studies(max_rows=100)

        if not studies:
            logger.info("No trials fetched")
            return

        count = upsert_trials(conn, studies, days_back=days_back)
        logger.info(f"Upserted {count} trials")
    except Exception as e:
        logger.error(f"ClinicalTrials ETL failed: {e}")
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
