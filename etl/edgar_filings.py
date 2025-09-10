#!/usr/bin/env python3
"""
SEC EDGAR Filings ETL Script
Fetches SEC filings per tracked company (via CIK) and stores in filings table
"""
import os
import requests
import psycopg2
from dotenv import load_dotenv
import logging
from datetime import datetime

from db import get_db_connection 

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_tracked_ciks(conn):
    """Get list of CIKs we want to track from companies table"""
    with conn.cursor() as cur:
        cur.execute("SELECT id, cik FROM public.companies WHERE cik IS NOT NULL")
        return {row[1].zfill(10): row[0] for row in cur.fetchall()}  # pad to 10 digits


def fetch_edgar_filings_for_cik(cik, limit=20):
    """Fetch filings for a single company from SEC submissions JSON API"""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {
        "User-Agent": os.getenv("EDGAR_USER_AGENT", "PharmaIntel ETL contact@pharmaintel.com")
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        filings = []
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])

        for i in range(min(len(forms), limit)):
            form = forms[i]
            accession = accession_numbers[i]
            filing_date = filing_dates[i]

            filings.append({
                "cik": cik,
                "form_type": form,
                "filing_date": filing_date,
                "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{accession}-index.htm"
            })

        return filings

    except Exception as e:
        logger.warning(f"Error fetching EDGAR filings for {cik}: {e}")
        return []


def extract_financial_data(_url):
    """Placeholder for parsing XBRL (skipped for now)."""
    return {"cash_usd": None, "rnd_expense_usd": None, "revenue_usd": None}


def upsert_filings(filings, tracked_ciks, conn):
    """Insert or update filings in DB"""
    logger.info("Upserting SEC filings...")

    relevant_forms = ("10-K", "10-Q", "8-K", "20-F", "S-1", "S-3")
    processed = 0

    with conn.cursor() as cur:
        for filing in filings:
            cik = filing.get("cik")
            form_type = filing.get("form_type")

            if not cik or not form_type:
                continue
            if cik not in tracked_ciks:
                continue
            if not any(form_type.startswith(f) for f in relevant_forms):
                continue

            company_id = tracked_ciks[cik]

            try:
                filing_date = None
                if filing.get("filing_date"):
                    try:
                        filing_date = datetime.strptime(filing["filing_date"], "%Y-%m-%d").date()
                    except Exception:
                        pass

                fin = extract_financial_data(filing.get("url", ""))

                cur.execute("""
                    INSERT INTO public.filings (company_id, cik, form_type, filing_date, url, cash_usd, rnd_expense_usd, revenue_usd)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (company_id, cik, form_type, filing_date, url) DO UPDATE SET
                        cash_usd = EXCLUDED.cash_usd,
                        rnd_expense_usd = EXCLUDED.rnd_expense_usd,
                        revenue_usd = EXCLUDED.revenue_usd
                """, (
                    company_id, cik, form_type, filing_date, filing.get("url", ""),
                    fin["cash_usd"], fin["rnd_expense_usd"], fin["revenue_usd"]
                ))

                processed += 1
            except Exception as e:
                logger.warning(f"Error inserting filing for {cik}: {e}")
                continue

        conn.commit()
        logger.info(f"Inserted/updated {processed} filings")


def main():
    try:
        conn = get_db_connection()
        logger.info("Connected to database")

        tracked_ciks = get_tracked_ciks(conn)
        logger.info(f"Tracking {len(tracked_ciks)} companies")

        all_filings = []
        for cik in tracked_ciks.keys():
            filings = fetch_edgar_filings_for_cik(cik, limit=20)
            all_filings.extend(filings)

        if all_filings:
            upsert_filings(all_filings, tracked_ciks, conn)
            logger.info("EDGAR ETL completed successfully!")
        else:
            logger.info("No filings fetched")

    except Exception as e:
        logger.error(f"EDGAR ETL failed: {e}")
        raise
    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    main()
