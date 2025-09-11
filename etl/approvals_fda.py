#!/usr/bin/env python3
"""
FDA Approvals ETL Script
Fetches FDA drug approvals from openFDA API and upserts into database
"""
import os
import requests
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
import logging
from datetime import datetime

from db import get_db_connection

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FDA_API_BASE = "https://api.fda.gov"


def fetch_fda_approvals(limit=100, max_skip=25000):
    """
    Fetch FDA approvals using pagination (limit + skip).
    Stops at skip limit (25,000 due to FDA API restriction).
    """
    approvals = []
    skip = 0

    while skip <= max_skip:
        params = {"limit": limit, "skip": skip}
        url = f"{FDA_API_BASE}/drug/drugsfda.json"

        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 404:
                logger.info("No more FDA approvals found.")
                break
            resp.raise_for_status()

            data = resp.json()
            results = data.get("results", [])
            if not results:
                break

            approvals.extend(results)
            logger.info(f"Fetched {len(results)} approvals from page skip={skip}")

            skip += limit
            if skip > max_skip:
                logger.warning("Reached FDA API skip limit (25,000). Stopping pagination.")
                break

        except Exception as e:
            logger.error(f"Error fetching FDA approvals: {e}")
            break

    logger.info(f"Total {len(approvals)} FDA approvals fetched")
    return approvals


def upsert_approvals(approvals, conn):
    """
    Upsert FDA approvals into the approvals table.
    Deduplicates by (application_number, submission_number).
    """
    logger.info(f"Upserting {len(approvals)} approvals into DB...")

    rows = []
    for app in approvals:
        app_num = app.get("application_number", "")
        sponsor = app.get("sponsor_name", "")

        for sub in app.get("submissions", []):
            rows.append((
                app_num,
                sponsor,
                sub.get("submission_type"),
                sub.get("submission_number"),
                sub.get("submission_status"),
                sub.get("submission_status_date"),
                sub.get("review_priority"),
                sub.get("submission_class_code"),
                sub.get("submission_class_code_description"),
                sub.get("submission_date"),
                psycopg2.extras.Json(app.get("products", []))  # ✅ store as JSONB
            ))

    if not rows:
        logger.info("No submission rows to insert.")
        return

    # Deduplicate before inserting
    rows = list({(r[0], r[3]): r for r in rows}.values())

    query = """
        INSERT INTO approvals (
            application_number, sponsor, submission_type, submission_number,
            submission_status, submission_status_date, review_priority,
            submission_class_code, submission_class_code_description,
            submission_date, products
        )
        VALUES %s
        ON CONFLICT (application_number, submission_number)
        DO UPDATE SET
            sponsor = EXCLUDED.sponsor,
            submission_type = EXCLUDED.submission_type,
            submission_status = EXCLUDED.submission_status,
            submission_status_date = EXCLUDED.submission_status_date,
            products = EXCLUDED.products;
    """

    with conn.cursor() as cur:
        extras.execute_values(cur, query, rows)
    conn.commit()
    logger.info(f"Inserted/updated {len(rows)} approvals")


def main():
    try:
        conn = get_db_connection()
        logger.info("Connected to database")

        approvals = fetch_fda_approvals(limit=100, max_skip=25000)

        if approvals:
            upsert_approvals(approvals, conn)  # ✅ fixed: pass conn
            logger.info("FDA approvals ETL completed successfully!")
        else:
            logger.info("No approvals to process")

    except Exception as e:
        logger.error(f"ETL failed: {e}")
        raise
    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    main()
